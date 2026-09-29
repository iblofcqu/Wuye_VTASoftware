"""会话记录与存储：session.json 原子读写 + 进程内锁。"""

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SESSION_FILE = "session.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_valid_session_id(value) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


@dataclass
class SessionRecord:
    session_id: str
    created_at: str = field(default_factory=utc_now_iso)
    artifacts: list = field(default_factory=list)
    jobs: list = field(default_factory=list)
    uploads: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionRecord":
        return cls(
            session_id=data["session_id"],
            created_at=data.get("created_at", utc_now_iso()),
            artifacts=list(data.get("artifacts", [])),
            jobs=list(data.get("jobs", [])),
            uploads=list(data.get("uploads", [])),
        )


class SessionStore:
    """以 `data/sessions/<uuid>/session.json` 为唯一真源的会话存储。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks_guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def _lock_for(self, session_id: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(session_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[session_id] = lock
            return lock

    def session_dir(self, session_id: str) -> Path:
        if not is_valid_session_id(session_id):
            raise ValueError(f"非法 session id: {session_id!r}")
        return self.root / str(session_id)

    def _session_file(self, session_id: str) -> Path:
        return self.session_dir(session_id) / SESSION_FILE

    def _read_unlocked(self, path: Path) -> SessionRecord:
        return SessionRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _write_unlocked(self, record: SessionRecord) -> None:
        path = self._session_file(record.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)

    def create(self) -> SessionRecord:
        record = SessionRecord(session_id=str(uuid.uuid4()))
        with self._lock_for(record.session_id):
            self._write_unlocked(record)
        return record

    def load(self, session_id: str) -> SessionRecord | None:
        path = self._session_file(session_id)
        if not path.exists():
            return None
        with self._lock_for(session_id):
            return self._read_unlocked(path)

    def update(self, session_id: str, mutate: Callable[[SessionRecord], None]) -> SessionRecord:
        """锁内读-改-写，保证并发更新不丢失、不损坏。"""
        with self._lock_for(session_id):
            path = self._session_file(session_id)
            if not path.exists():
                raise FileNotFoundError(f"会话不存在: {session_id}")
            record = self._read_unlocked(path)
            mutate(record)
            self._write_unlocked(record)
            return record
