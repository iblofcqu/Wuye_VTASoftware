"""任务 5.1：任务状态机、进程池容量与 Web 响应性。"""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.sessions import SessionStore
from app.jobs.runner import JobRunner
from app.main import create_app


def fast_tool(params, inputs, input_names, work_dir, progress):
    output = Path(work_dir) / "out.xyz"
    output.write_text("data", encoding="utf-8")
    return {
        "outputs": [{"path": str(output), "display_name": "out.xyz", "kind": "pointcloud"}],
        "summary": {"echo": params.get("echo")},
        "internal_outputs": {},
    }


def slow_tool(params, inputs, input_names, work_dir, progress):
    time.sleep(float(params.get("seconds", 1.0)))
    return fast_tool(params, inputs, input_names, work_dir, progress)


def _wait_for(runner: JobRunner, session_id: str, job_id: str, predicate, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        view = runner.view_job(session_id, job_id)
        assert view is not None
        if predicate(view):
            return view
        time.sleep(0.05)
    raise AssertionError(f"等待超时: {runner.view_job(session_id, job_id)}")


def test_job_lifecycle_success(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    runner = JobRunner(store, registry={"fast": fast_tool}, pool_size=1)
    try:
        job = runner.submit(session.session_id, "fast", {"echo": "hi"}, {})
        view = _wait_for(runner, session.session_id, job["id"], lambda v: v["status"] == "succeeded")
        assert view["result"]["artifacts"][0]["name"] == "out.xyz"
        assert view["result"]["summary"] == {"echo": "hi"}
        assert store.load(session.session_id).artifacts[0]["name"] == "out.xyz"
    finally:
        runner.shutdown()


def test_pool_capacity_queues_excess_jobs(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    runner = JobRunner(store, registry={"slow": slow_tool}, pool_size=1)
    try:
        first = runner.submit(session.session_id, "slow", {"seconds": 1.5}, {})
        second = runner.submit(session.session_id, "slow", {"seconds": 0.1}, {})

        deadline = time.time() + 10
        observed = False
        while time.time() < deadline:
            first_view = runner.view_job(session.session_id, first["id"])
            second_view = runner.view_job(session.session_id, second["id"])
            if first_view["status"] == "running" and second_view["status"] == "queued":
                observed = True
                break
            time.sleep(0.02)
        assert observed, "未观察到 running + queued 并存"

        _wait_for(runner, session.session_id, first["id"], lambda v: v["status"] == "succeeded")
        _wait_for(runner, session.session_id, second["id"], lambda v: v["status"] == "succeeded")
    finally:
        runner.shutdown()


def test_web_stays_responsive_during_long_task(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions", tool_registry={"slow": slow_tool}, job_pool_size=1)
    with TestClient(app) as client:
        client.get("/api/session")
        submitted = client.post("/api/tools/slow/jobs", json={"inputs": {}, "params": {"seconds": 2.0}})
        assert submitted.status_code == 202, submitted.text
        job_id = submitted.json()["id"]

        became_running = False
        deadline = time.time() + 10
        while time.time() < deadline:
            started = time.perf_counter()
            status = client.get(f"/api/jobs/{job_id}")
            session_response = client.get("/api/session")
            elapsed = time.perf_counter() - started
            assert status.status_code == 200 and session_response.status_code == 200
            assert elapsed < 1.0, f"任务运行期间查询耗时过长: {elapsed:.2f}s"
            if status.json()["status"] == "running":
                became_running = True
                break
            time.sleep(0.05)
        assert became_running, "任务未进入 running"

        deadline = time.time() + 20
        while time.time() < deadline:
            if client.get(f"/api/jobs/{job_id}").json()["status"] == "succeeded":
                break
            time.sleep(0.1)
        else:
            raise AssertionError("任务未完成")

        finished = client.get(f"/api/jobs/{job_id}").json()
        assert finished["result"]["artifacts"][0]["name"] == "out.xyz"
