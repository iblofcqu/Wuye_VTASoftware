"""报告生成超时与阶段诊断测试。"""

import json
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

import pytest

from app import config
from app.jobs import tools
from app.main import create_app
from app.report import supervisor
from app.services import quality
from tests.report_timeout_helpers import (
    blocking_report_target,
    quick_report_target,
    supervised_report_tool,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENE = FIXTURES / "sample_scene.xyz"
BIM = FIXTURES / "sample_bim.xyz"


def test_report_timeout_config_default_and_bounds(monkeypatch):
    monkeypatch.delenv("WUYE_REPORT_TIMEOUT_SECONDS", raising=False)
    assert config.parse_report_timeout_seconds() == 300
    assert config.parse_report_timeout_seconds("30") == 30
    assert config.parse_report_timeout_seconds("3600") == 3600
    for bad in ("29", "3601", "abc", ""):
        with pytest.raises(ValueError):
            config.parse_report_timeout_seconds(bad)


def test_report_timeout_error_includes_timeout_and_stage():
    error = supervisor.ReportTimeoutError(300, "编译 PDF（latexmk/xelatex）")
    assert "300" in str(error)
    assert "编译 PDF（latexmk/xelatex）" in str(error)


def test_report_timeout_error_is_picklable():
    error = supervisor.ReportTimeoutError(300, "编译 PDF（latexmk/xelatex）")
    restored = pickle.loads(pickle.dumps(error))
    assert restored.timeout_seconds == 300
    assert restored.stage == "编译 PDF（latexmk/xelatex）"
    assert str(restored) == str(error)


def test_run_report_phase_returns_target_result(tmp_path: Path):
    result = supervisor.run_report_phase(
        quick_report_target,
        work_dir=tmp_path,
        timeout_seconds=5,
    )
    assert result == {"ok": True}
    assert json.loads((tmp_path / supervisor.REPORT_STATE_FILE).read_text(encoding="utf-8"))[
        "stage"
    ] == "快速阶段"


def test_run_report_phase_times_out_with_last_stage(tmp_path: Path):
    started = time.monotonic()
    with pytest.raises(supervisor.ReportTimeoutError) as exc_info:
        supervisor.run_report_phase(
            blocking_report_target,
            work_dir=tmp_path,
            timeout_seconds=1,
        )

    assert exc_info.value.stage == "阻塞阶段"
    assert "1" in str(exc_info.value)
    assert time.monotonic() - started < 10


def test_report_phase_can_run_after_timeout(tmp_path: Path):
    with pytest.raises(supervisor.ReportTimeoutError):
        supervisor.run_report_phase(
            blocking_report_target,
            work_dir=tmp_path,
            timeout_seconds=1,
        )

    result = supervisor.run_report_phase(
        quick_report_target,
        work_dir=tmp_path,
        timeout_seconds=5,
    )
    assert result == {"ok": True}


def test_terminate_process_tree_kills_child():
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=(os.name == "posix"),
    )
    try:
        supervisor.terminate_process_tree(child.pid)
        child.wait(timeout=10)
        assert child.poll() is not None
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def test_terminate_process_tree_windows_uses_taskkill(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

        class Result:
            returncode = 1

        return Result()

    monkeypatch.setattr(supervisor.os, "name", "nt")
    monkeypatch.setattr(supervisor.subprocess, "run", fake_run)

    supervisor.terminate_process_tree(1234)

    assert calls
    assert calls[0][0][:4] == ["taskkill", "/F", "/T", "/PID"]
    assert "1234" in calls[0][0]


def test_quality_assess_emits_report_stages(tmp_path: Path, monkeypatch):
    stages: list[str] = []
    progress_stages: list[tuple[str, int, int]] = []

    class FakeFigure:
        def to_json(self):
            return '{"data": []}'

        def write_image(self, *args, **kwargs):
            return None

    monkeypatch.setattr(quality.figures, "draw1", lambda *args, **kwargs: None)
    monkeypatch.setattr(quality.figures, "draw2", lambda *args, **kwargs: None)
    monkeypatch.setattr(quality.figures, "draw_error2", lambda *args, **kwargs: None)
    monkeypatch.setattr(quality.figures, "show_clum", lambda *args, **kwargs: FakeFigure())
    monkeypatch.setattr(quality.pdf, "QA_Report", lambda *args, **kwargs: None)

    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "out"
    cache_dir.mkdir()
    output_dir.mkdir()

    quality.assess(
        SCENE,
        BIM,
        output_dir,
        cache_dir,
        unit="m",
        method="Point2Point",
        distance=0.05,
        ratio=0.05,
        progress=lambda stage, done, total: progress_stages.append((stage, done, total)),
        report_progress=stages.append,
    )

    assert [done for _, done, _ in progress_stages] == [1, 2, 3, 4]
    assert stages == [
        "渲染输入点云图",
        "渲染环境/检测点图",
        "渲染偏差云图",
        "导出偏差直方图（Plotly/Kaleido）",
        "编译 PDF（latexmk/xelatex）",
    ]


def test_quality_assess_routes_through_report_supervisor(tmp_path: Path, monkeypatch):
    calls = []

    def fake_run_report_phase(target, args=(), kwargs=None, **options):
        calls.append((target, args, kwargs, options))
        raise supervisor.ReportTimeoutError(1, "测试阶段")

    monkeypatch.setattr(tools, "run_report_phase", fake_run_report_phase)

    with pytest.raises(supervisor.ReportTimeoutError):
        tools.run_quality_assess(
            {
                "unit": "m",
                "method": "Point2Point",
                "distance": 0.05,
                "ratio": 0.05,
            },
            {"scan": "/tmp/scan.xyz", "bim": "/tmp/bim.xyz"},
            {"scan": "scan.xyz", "bim": "bim.xyz"},
            tmp_path,
            lambda *args: None,
        )

    assert calls
    assert calls[0][0] is quality.assess
    assert calls[0][3]["timeout_seconds"] == config.REPORT_TIMEOUT_SECONDS


def test_timeout_releases_worker_for_next_job(tmp_path: Path):
    app = create_app(
        tmp_path / "sessions",
        tool_registry={"report-timeout-test": supervised_report_tool},
        job_pool_size=1,
    )

    with TestClient(app) as client:
        client.get("/api/session")
        first = client.post(
            "/api/tools/report-timeout-test/jobs",
            json={"inputs": {}, "params": {"mode": "blocking", "timeout_seconds": 1}},
        ).json()
        second = client.post(
            "/api/tools/report-timeout-test/jobs",
            json={"inputs": {}, "params": {"mode": "quick", "timeout_seconds": 5}},
        ).json()

        deadline = time.monotonic() + 20
        first_view = None
        second_view = None
        while time.monotonic() < deadline:
            first_view = client.get(f"/api/jobs/{first['id']}").json()
            second_view = client.get(f"/api/jobs/{second['id']}").json()
            if first_view["status"] in {"failed", "succeeded"} and second_view["status"] in {
                "failed",
                "succeeded",
            }:
                break
            time.sleep(0.1)

    assert first_view is not None and first_view["status"] == "failed"
    assert "阻塞阶段" in (first_view.get("error") or "")
    assert second_view is not None and second_view["status"] == "succeeded"
