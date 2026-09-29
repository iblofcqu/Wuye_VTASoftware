"""任务 9.1：/api/health 自检（缺失显式列项，齐全时通过）。"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.core import health
from app.main import create_app


def test_health_endpoint_structure(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] in {"ok", "degraded"}
        assert [check["name"] for check in body["checks"]] == [
            "tex",
            "chromium",
            "offscreen_rendering",
            "chinese_fonts",
        ]
        for check in body["checks"]:
            assert isinstance(check["ok"], bool)
            assert check["detail"]


def test_missing_tex_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(
        health.shutil, "which", lambda name: None if name in {"latexmk", "xelatex"} else "/usr/bin/echo"
    )
    result = health.check_tex()
    assert result.ok is False
    assert "latexmk" in result.detail and "xelatex" in result.detail


def test_missing_chromium_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(health.shutil, "which", lambda name: None)
    result = health.check_chromium()
    assert result.ok is False
    assert "Chrome" in result.detail


def test_check_exception_is_reported_as_failure() -> None:
    def broken() -> health.HealthCheck:
        raise RuntimeError("boom")

    results = health.run_health_checks([broken])
    assert results[0]["ok"] is False
    assert "boom" in results[0]["detail"]
