"""任务 3.1：会话存储的原子性/恢复能力与中间件 cookie 行为。"""

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import SESSION_COOKIE_NAME
from app.core.sessions import SessionStore, is_valid_session_id
from app.main import create_app


def test_store_persists_and_recovers(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    record = store.create()

    def append(rec):
        rec.artifacts.append({"id": "a1", "name": "sample.xyz"})

    store.update(record.session_id, append)

    restarted = SessionStore(tmp_path / "sessions")
    loaded = restarted.load(record.session_id)
    assert loaded is not None
    assert loaded.artifacts == [{"id": "a1", "name": "sample.xyz"}]
    assert loaded.created_at == record.created_at


def test_concurrent_updates_do_not_corrupt(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    record = store.create()

    def worker(worker_id: int) -> None:
        for index in range(10):
            store.update(record.session_id, lambda rec: rec.artifacts.append({"w": worker_id, "i": index}))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    session_file = store.session_dir(record.session_id) / "session.json"
    data = json.loads(session_file.read_text(encoding="utf-8"))
    assert len(data["artifacts"]) == 160
    assert not list(session_file.parent.glob("*.tmp")), "不应残留临时文件"


def test_invalid_session_id_rejected(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    with pytest.raises(ValueError):
        store.load("../../etc/passwd")
    assert not is_valid_session_id("not-a-uuid")


def test_middleware_sets_persistent_cookie_and_reuses_session(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "sessions"))
    first = client.get("/api/session")
    assert first.status_code == 200
    session_id = first.json()["session_id"]
    assert is_valid_session_id(session_id)

    set_cookie = first.headers["set-cookie"]
    assert SESSION_COOKIE_NAME in set_cookie and "HttpOnly" in set_cookie and "Max-Age" in set_cookie

    second = client.get("/api/session")
    assert second.json()["session_id"] == session_id

    other = TestClient(create_app(tmp_path / "sessions")).get("/api/session")
    assert other.json()["session_id"] != session_id


def test_middleware_replaces_invalid_cookie(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    client = TestClient(create_app(root))
    client.cookies.set(SESSION_COOKIE_NAME, "../../evil")
    response = client.get("/api/session")
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    assert is_valid_session_id(session_id)
    assert (root / session_id / "session.json").exists()
    assert not (root.parent / "evil").exists()
