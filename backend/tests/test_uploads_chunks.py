"""任务 4.1：上传初始化与分片接收（幂等、SHA-256 校验、边界）。"""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.core.uploads import chunk_path, get_upload
from app.main import create_app


def _setup(tmp_path: Path):
    app = create_app(tmp_path / "sessions")
    client = TestClient(app)
    session_id = client.get("/api/session").json()["session_id"]
    return app, client, session_id


def _init_upload(client: TestClient, filename: str, size: int, chunk_size: int = 1024) -> dict:
    response = client.post(
        "/api/uploads", json={"filename": filename, "size": size, "chunk_size": chunk_size}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _put_chunk(client: TestClient, upload_id: str, index: int, data: bytes, checksum: str | None = None):
    headers = {"X-Chunk-SHA256": checksum or hashlib.sha256(data).hexdigest()}
    return client.put(f"/api/uploads/{upload_id}/chunks/{index}", content=data, headers=headers)


def test_chunk_upload_and_idempotent_resend(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    payload = bytes(range(256)) * 10  # 2560 字节 -> 3 个分片（1024/1024/512）
    info = _init_upload(client, "scan.xyz", len(payload))
    assert info["total_chunks"] == 3

    first = payload[:1024]
    response = _put_chunk(client, info["upload_id"], 0, first)
    assert response.status_code == 200, response.text
    assert response.json()["received"] == 1
    assert response.json()["received_indices"] == [0]

    again = _put_chunk(client, info["upload_id"], 0, first)
    assert again.status_code == 200
    assert again.json()["received_indices"] == [0]  # 幂等

    store = app.state.session_store
    stored = chunk_path(store, session_id, info["upload_id"], 0).read_bytes()
    assert stored == first
    assert get_upload(store, session_id, info["upload_id"]).received == [0]


def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    payload = b"x" * 2048
    info = _init_upload(client, "scan.xyz", len(payload))

    response = _put_chunk(client, info["upload_id"], 0, payload[:1024], checksum="0" * 64)
    assert response.status_code == 400
    assert "校验" in response.json()["detail"]

    store = app.state.session_store
    assert get_upload(store, session_id, info["upload_id"]).received == []
    assert not chunk_path(store, session_id, info["upload_id"], 0).exists()


def test_index_and_length_bounds(tmp_path: Path) -> None:
    _, client, _ = _setup(tmp_path)
    payload = b"y" * 1500
    info = _init_upload(client, "scan.xyz", len(payload))

    assert _put_chunk(client, info["upload_id"], 2, b"z" * 100).status_code == 400  # 越界
    assert _put_chunk(client, info["upload_id"], 0, b"z" * 100).status_code == 400  # 过短
    assert _put_chunk(client, info["upload_id"], 0, b"z" * 2048).status_code == 413  # 超长
    assert _put_chunk(client, info["upload_id"], 1, b"z" * 476).status_code == 200  # 末片正确长度


def test_init_validation_and_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, client, _ = _setup(tmp_path)

    assert client.post("/api/uploads", json={"filename": "a.xyz", "size": 0}).status_code == 400
    assert (
        client.post("/api/uploads", json={"filename": "a.xyz", "size": 2048, "chunk_size": 10}).status_code
        == 400
    )

    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 100)
    too_large = client.post("/api/uploads", json={"filename": "a.xyz", "size": 101})
    assert too_large.status_code == 413


def test_filename_is_sanitized(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    info = _init_upload(client, "../sub/scan.xyz", 1024)
    assert info["filename"] == "scan.xyz"
    assert get_upload(app.state.session_store, session_id, info["upload_id"]).filename == "scan.xyz"


def test_upload_is_session_scoped(tmp_path: Path) -> None:
    app, client_a, _ = _setup(tmp_path)
    client_b = TestClient(app)
    client_b.get("/api/session")  # 建立第二个会话

    info = _init_upload(client_a, "scan.xyz", 1024)
    response = _put_chunk(client_b, info["upload_id"], 0, b"a" * 1024)
    assert response.status_code == 404


def test_chunk_checksum_header_required(tmp_path: Path) -> None:
    _, client, _ = _setup(tmp_path)
    info = _init_upload(client, "scan.xyz", 1024)
    response = client.put(f"/api/uploads/{info['upload_id']}/chunks/0", content=b"a" * 1024)
    assert response.status_code == 400
    assert "X-Chunk-SHA256" in response.json()["detail"]
