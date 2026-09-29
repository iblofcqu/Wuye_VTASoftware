"""会话清空 API：SSE 事件、冲突保护和会话隔离。"""

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.session_cleanup import CleanupResult, SessionCleanupBusy
from app.main import create_app


def _parse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = ""
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if event_name:
            events.append((event_name, data or {}))
    return events


def _wait_job(client: TestClient, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        view = client.get(f"/api/jobs/{job_id}").json()
        if view["status"] in {"succeeded", "failed", "interrupted"}:
            return view
        time.sleep(0.05)
    raise AssertionError(f"等待任务完成超时: {job_id}")


def slow_tool(params, inputs, input_names, work_dir, progress):
    time.sleep(0.5)
    return {"outputs": [], "summary": {}, "internal_outputs": {}}


def test_clear_session_streams_started_then_success_and_isolates_other_sessions(
    tmp_path: Path,
) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    assert app.state.session_cleanup is not None

    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        other = store.create()
        marker = store.session_dir(session_id) / "artifacts" / "sample.bin"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("data", encoding="utf-8")
        other_marker = store.session_dir(other.session_id) / "artifacts" / "other.bin"
        other_marker.parent.mkdir(parents=True, exist_ok=True)
        other_marker.write_text("other", encoding="utf-8")

        response = client.post("/api/session/clear", headers={"Accept": "text/event-stream"})

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _parse_events(response.text)
        assert [name for name, _ in events] == ["started", "success"]
        assert events[0][1]["state"] == "started"
        assert events[1][1]["state"] == "success"
        assert not store.session_dir(session_id).exists()
        assert other_marker.exists()
        assert store.load(other.session_id) is not None

        next_session = client.get("/api/session").json()
        assert next_session["session_id"] != session_id
        assert next_session["artifacts"] == []
        assert next_session["jobs"] == []
        assert next_session["uploads"] == []


def test_clear_rejects_active_job_and_keeps_directory(tmp_path: Path) -> None:
    app = create_app(
        tmp_path / "sessions",
        tool_registry={"slow": slow_tool},
        job_pool_size=1,
    )
    store = app.state.session_store

    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        submitted = client.post(
            "/api/tools/slow/jobs",
            json={"inputs": {}, "params": {}},
        )
        assert submitted.status_code == 202

        response = client.post("/api/session/clear")

        assert response.status_code == 409
        assert "任务" in response.json()["detail"]
        assert store.session_dir(session_id).exists()
        final = _wait_job(client, submitted.json()["id"])
        assert final["status"] == "succeeded"


def test_clear_rejects_unfinished_upload_and_keeps_directory(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store

    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        store.update(
            session_id,
            lambda record: record.uploads.append({"id": "upload-1", "status": "uploading"}),
        )

        response = client.post("/api/session/clear")

        assert response.status_code == 409
        assert "上传" in response.json()["detail"]
        assert store.session_dir(session_id).exists()


def test_clear_rejects_existing_cleanup_guard(tmp_path: Path) -> None:
    class BusyManager:
        def start(self, store, session_id):
            raise SessionCleanupBusy(f"会话正在清空: {session_id}")

    app = create_app(tmp_path / "sessions")
    app.state.session_cleanup = BusyManager()
    store = app.state.session_store

    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        response = client.post("/api/session/clear")

        assert response.status_code == 409
        assert "正在清空" in response.json()["detail"]
        assert store.session_dir(session_id).exists()


def test_clear_streams_error_without_success(tmp_path: Path) -> None:
    class FailedOperation:
        def wait(self):
            return CleanupResult(False, "模拟删除失败")

    class FailedManager:
        def start(self, store, session_id):
            return FailedOperation()

    app = create_app(tmp_path / "sessions")
    app.state.session_cleanup = FailedManager()
    store = app.state.session_store

    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        response = client.post("/api/session/clear")

        assert response.status_code == 200
        events = _parse_events(response.text)
        assert [name for name, _ in events] == ["started", "error"]
        assert events[1][1]["message"] == "模拟删除失败"
        assert "success" not in [name for name, _ in events]
        assert store.session_dir(session_id).exists()
