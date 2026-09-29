"""任务记录在会话清单中的读写。"""

from app.core.sessions import SessionStore, utc_now_iso
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
