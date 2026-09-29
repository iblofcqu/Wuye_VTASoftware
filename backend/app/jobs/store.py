"""任务记录在会话清单中的读写。"""

from app.core.sessions import SessionStore, is_valid_session_id, utc_now_iso
from app.jobs.models import JobRecord


def add_job(store: SessionStore, session_id: str, job: JobRecord) -> dict:
    store.update(session_id, lambda session: session.jobs.append(job.to_dict()))
    return job.to_dict()


def get_job(store: SessionStore, session_id: str, job_id: str) -> dict | None:
    session = store.load(session_id)
    if session is None:
        return None
    for entry in session.jobs:
        if entry.get("id") == job_id:
            return dict(entry)
    return None


def update_job(store: SessionStore, session_id: str, job_id: str, mutate) -> dict | None:
    def wrapper(session) -> None:
        for entry in session.jobs:
            if entry.get("id") == job_id:
                mutate(entry)
                entry["updated_at"] = utc_now_iso()
                return
        raise FileNotFoundError(f"任务不存在: {job_id}")

    store.update(session_id, wrapper)
    return get_job(store, session_id, job_id)


def interrupt_leftover_jobs(store: SessionStore) -> int:
    """服务启动时把遗留的 queued/running 任务显式标记为 interrupted。"""
    interrupted = 0
    if not store.root.exists():
        return 0
    for session_dir in sorted(store.root.iterdir()):
        session_id = session_dir.name
        if not session_dir.is_dir() or not is_valid_session_id(session_id):
            continue
        record = store.load(session_id)
        if record is None:
            continue
        leftover = [job for job in record.jobs if job.get("status") in {"queued", "running"}]
        if not leftover:
            continue

        def mark(session) -> None:
            for job in session.jobs:
                if job.get("status") in {"queued", "running"}:
                    job["status"] = "interrupted"
                    job["error"] = "服务重启导致任务中断"
                    job["updated_at"] = utc_now_iso()

        store.update(session_id, mark)
        interrupted += len(leftover)
    return interrupted
