"""任务 5.3：失败显式化与重启中断语义。"""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import SESSION_COOKIE_NAME
from app.core.sessions import SessionStore
from app.jobs import store as job_store
from app.jobs.models import new_job
from app.jobs.runner import JobRunner
from app.main import create_app


def failing_tool(params, inputs, work_dir, progress):
    raise ValueError("参数坏掉了")


def _wait_for(runner: JobRunner, session_id: str, job_id: str, predicate, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        view = runner.view_job(session_id, job_id)
        assert view is not None
        if predicate(view):
            return view
        time.sleep(0.05)
    raise AssertionError(f"等待超时: {runner.view_job(session_id, job_id)}")


def test_failure_is_explicit_and_produces_no_artifact(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    runner = JobRunner(store, registry={"fail": failing_tool}, pool_size=1)
    try:
        job = runner.submit(session.session_id, "fail", {}, {})
        view = _wait_for(runner, session.session_id, job["id"], lambda v: v["status"] == "failed")
        assert "参数坏掉了" in view["error"]
        assert view["result"] is None
        assert store.load(session.session_id).artifacts == []
    finally:
        runner.shutdown()


def test_startup_interrupts_leftover_jobs(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    store = SessionStore(root)
    session = store.create()
    leftover = new_job("downsample-voxel")
    leftover.status = "running"
    job_store.add_job(store, session.session_id, leftover)
    queued = new_job("scale")
    job_store.add_job(store, session.session_id, queued)

    app = create_app(root)
    with TestClient(app) as client:
        client.cookies.set(SESSION_COOKIE_NAME, session.session_id)  # 复用遗留任务所属会话
        # 启动时已把遗留任务标记为中断
        view = client.get(f"/api/jobs/{leftover.id}")
        assert view.status_code == 200
        body = view.json()
        assert body["status"] == "interrupted"
        assert "服务重启" in body["error"]

        second = client.get(f"/api/jobs/{queued.id}").json()
        assert second["status"] == "interrupted"


def test_interrupt_helper_counts_and_is_idempotent(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    job = new_job("scale")
    job_store.add_job(store, session.session_id, job)

    assert job_store.interrupt_leftover_jobs(store) == 1
    assert job_store.interrupt_leftover_jobs(store) == 0  # 已中断不再重复计数
    assert job_store.get_job(store, session.session_id, job.id)["status"] == "interrupted"
