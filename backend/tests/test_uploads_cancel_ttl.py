"""任务 4.3：上传取消与过期清理。"""

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.uploads import get_upload, purge_expired_uploads
from app.main import create_app


def _setup(tmp_path: Path):
    app = create_app(tmp_path / "sessions")
    client = TestClient(app)
    session_id = client.get("/api/session").json()["session_id"]
    return app, client, session_id


def _init(client: TestClient, name: str, size: int, chunk: int = 1024) -> dict:
    response = client.post("/api/uploads", json={"filename": name, "size": size, "chunk_size": chunk})
    assert response.status_code == 201, response.text
    return response.json()


def _put(client: TestClient, upload_id: str, index: int, data: bytes):
    headers = {"X-Chunk-SHA256": hashlib.sha256(data).hexdigest()}
    return client.put(f"/api/uploads/{upload_id}/chunks/{index}", content=data, headers=headers)


def test_cancel_removes_chunks_and_is_idempotent(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    payload = b"a" * 2048
    info = _init(client, "scan.xyz", len(payload))
    _put(client, info["upload_id"], 0, payload[:1024])

    upload_dir = app.state.session_store.session_dir(session_id) / "uploads" / info["upload_id"]
    assert upload_dir.exists()

    first = client.delete(f"/api/uploads/{info['upload_id']}")
    assert first.status_code == 200 and first.json()["status"] == "aborted"
    assert not upload_dir.exists()

    again = client.delete(f"/api/uploads/{info['upload_id']}")
    assert again.status_code == 200 and again.json()["status"] == "aborted"


def test_cancel_completed_upload_conflicts(tmp_path: Path) -> None:
    _, client, _ = _setup(tmp_path)
    payload = b"b" * 1024
    info = _init(client, "scan.xyz", len(payload))
    _put(client, info["upload_id"], 0, payload)
    assert client.post(f"/api/uploads/{info['upload_id']}/complete").status_code == 200
    assert client.delete(f"/api/uploads/{info['upload_id']}").status_code == 409


def test_expired_upload_is_purged_but_completed_is_kept(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    store = app.state.session_store

    stale = _init(client, "stale.xyz", 1024)
    _put(client, stale["upload_id"], 0, b"x" * 1024)
    done = _init(client, "done.xyz", 1024)
    _put(client, done["upload_id"], 0, b"y" * 1024)
    client.post(f"/api/uploads/{done['upload_id']}/complete")

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    store.update(
        session_id,
        lambda record: [
            entry.update({"expires_at": past})
            for entry in record.uploads
            if entry["id"] == stale["upload_id"]
        ],
    )

    purged = purge_expired_uploads(store)
    assert purged == [stale["upload_id"]]
    assert get_upload(store, session_id, stale["upload_id"]).status == "aborted"
    assert not (store.session_dir(session_id) / "uploads" / stale["upload_id"]).exists()
    assert get_upload(store, session_id, done["upload_id"]).status == "completed"


def test_new_upload_lazily_purges_expired(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    store = app.state.session_store

    stale = _init(client, "stale.xyz", 1024)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    store.update(
        session_id,
        lambda record: [
            entry.update({"expires_at": past}) for entry in record.uploads if entry["id"] == stale["upload_id"]
        ],
    )

    fresh = _init(client, "fresh.xyz", 1024)
    assert get_upload(store, session_id, stale["upload_id"]).status == "aborted"
    assert get_upload(store, session_id, fresh["upload_id"]).status == "uploading"
