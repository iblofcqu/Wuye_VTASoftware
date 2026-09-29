"""任务 5.2：阶段进度回传（含真实质量评估任务的第 N/4 步）。"""

import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.artifacts import register_artifact
from app.core.preview import parse_preview_header
from app.main import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures"

requires_tex = pytest.mark.skipif(
    shutil.which("latexmk") is None or shutil.which("xelatex") is None,
    reason="真实质量评估需要 latexmk + xelatex（部署由 /api/health 检查）",
)


def progress_tool(params, inputs, input_names, work_dir, progress):
    total = 4
    for step in range(1, total + 1):
        progress(f"第 {step}/{total} 步 处理", step, total)
        time.sleep(0.15)
    output = Path(work_dir) / "out.xyz"
    output.write_text("data", encoding="utf-8")
    return {
        "outputs": [{"path": str(output), "display_name": "out.xyz", "kind": "pointcloud"}],
        "summary": {},
        "internal_outputs": {},
    }


def _poll(client: TestClient, job_id: str, predicate, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        view = client.get(f"/api/jobs/{job_id}").json()
        if predicate(view):
            return view
        time.sleep(0.1)
    raise AssertionError(f"等待超时: {client.get(f'/api/jobs/{job_id}').json()}")


def test_progress_stages_are_visible(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions", tool_registry={"progress": progress_tool}, job_pool_size=1)
    with TestClient(app) as client:
        client.get("/api/session")
        job_id = client.post("/api/tools/progress/jobs", json={"inputs": {}, "params": {}}).json()["id"]

        observed: set[tuple[int, int]] = set()
        deadline = time.time() + 15
        while time.time() < deadline and len(observed) < 4:
            view = client.get(f"/api/jobs/{job_id}").json()
            progress = view.get("progress")
            if progress:
                observed.add((progress["done"], progress["total"]))
            time.sleep(0.02)
        assert observed == {(1, 4), (2, 4), (3, 4), (4, 4)}

        final = _poll(client, job_id, lambda v: v["status"] == "succeeded")
        assert final["progress"]["total"] == 4  # 完成后仍保留最后进度


@requires_tex
def test_quality_assess_job_reports_four_steps(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        scan = register_artifact(
            store, session_id, FIXTURES / "sample_scene.xyz", name="scan.xyz", kind="pointcloud"
        )
        bim = register_artifact(
            store, session_id, FIXTURES / "sample_bim.xyz", name="bim.xyz", kind="pointcloud"
        )

        response = client.post(
            "/api/tools/quality-assess/jobs",
            json={
                "inputs": {"scan": scan.id, "bim": bim.id},
                "params": {"unit": "m", "method": "Point2Point", "distance": 0.05, "ratio": 0.05},
            },
        )
        assert response.status_code == 202, response.text
        job_id = response.json()["id"]

        stages: list[str] = []
        deadline = time.time() + 90
        while time.time() < deadline:
            view = client.get(f"/api/jobs/{job_id}").json()
            progress = view.get("progress")
            if progress and progress["stage"] not in stages:
                stages.append(progress["stage"])
            if view["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.1)

        final = client.get(f"/api/jobs/{job_id}").json()
        assert final["status"] == "succeeded", final.get("error")
        assert any(stage.startswith("第1/4步") for stage in stages), stages
        assert any(stage.startswith("第4/4步") for stage in stages), stages
        assert final["result"]["summary"]["check_num"] > 0
        assert final["result"]["summary"]["figure"]["data"]
        assert final["result"]["artifacts"][0]["kind"] == "report"
        assert final["result"]["artifacts"][0]["name"].startswith("scan几何质量评估报告")

        preview = client.get(f"/api/jobs/{job_id}/preview")
        assert preview.status_code == 200, preview.text
        header = parse_preview_header(preview.content)
        assert header["fields"] == ["x", "y", "z", "scalar"]
        assert header["scalar_unit"] == "mm" and header["colormap"] == "seismic"
