"""任务 4.2：上传状态查询与完成合并（整体校验、幂等、产物登记）。"""

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.uploads import chunk_path, get_upload
from app.main import create_app


def _setup(tmp_path: Path):
    app = create_app(tmp_path / "sessions")
    client = TestClient(app)
    session_id = client.get("/api/session").json()["session_id"]
    return app, client, session_id


def _init_upload(client: TestClient, filename: str, size: int, chunk_size: int = 1024) -> dict:
    response = client.post("/api/uploads", json={"filename": filename, "size": size, "chunk_size": chunk_size})
    assert response.status_code == 201, response.text
    return response.json()


def _put(client: TestClient, upload_id: str, index: int, data: bytes):
    headers = {"X-Chunk-SHA256": hashlib.sha256(data).hexdigest()}
    return client.put(f"/api/uploads/{upload_id}/chunks/{index}", content=data, headers=headers)


def test_status_and_complete_idempotent(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    payload = bytes(range(256)) * 10
    info = _init_upload(client, "scan.xyz", len(payload))
    upload_id = info["upload_id"]

    _put(client, upload_id, 0, payload[:1024])
    _put(client, upload_id, 1, payload[1024:2048])
    status = client.get(f"/api/uploads/{upload_id}").json()
    assert status["received"] == 2 and status["missing_indices"] == [2] and status["status"] == "uploading"
    assert status["kind"] == "pointcloud"

    assert client.post(f"/api/uploads/{upload_id}/complete").status_code == 409  # 缺分片
    _put(client, upload_id, 2, payload[2048:])
    assert client.get(f"/api/uploads/{upload_id}").json()["missing_indices"] == []

    completed = client.post(f"/api/uploads/{upload_id}/complete")
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "completed"
    artifact = body["artifact"]
    assert artifact["name"] == "scan.xyz" and artifact["kind"] == "pointcloud"
    assert "path" not in artifact

    download = client.get(f"/api/artifacts/{artifact['id']}/download")
    assert download.status_code == 200 and download.content == payload

    again = client.post(f"/api/uploads/{upload_id}/complete")
    assert again.status_code == 200
    assert again.json()["artifact"]["id"] == artifact["id"]  # 幂等

    assert not (app.state.session_store.session_dir(session_id) / "uploads" / upload_id).exists()
    assert get_upload(app.state.session_store, session_id, upload_id).status == "completed"


def test_mesh_kind_inferred(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    payload = b"solid mesh" * 200
    info = _init_upload(client, "model.stl", len(payload), chunk_size=4096)
    assert info["kind"] == "mesh" and info["total_chunks"] == 1
    _put(client, info["upload_id"], 0, payload)
    assert client.post(f"/api/uploads/{info['upload_id']}/complete").status_code == 200
    artifact_id = get_upload(app.state.session_store, session_id, info["upload_id"]).artifact_id
    assert artifact_id is not None


def test_unsupported_extension_rejected(tmp_path: Path) -> None:
    _, client, _ = _setup(tmp_path)
    response = client.post("/api/uploads", json={"filename": "virus.exe", "size": 1024})
    assert response.status_code == 400
    assert "不支持" in response.json()["detail"]


def test_tampered_chunk_is_detected_and_must_be_resent(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    payload = b"a" * 2048
    info = _init_upload(client, "scan.xyz", len(payload))
    upload_id = info["upload_id"]
    _put(client, upload_id, 0, payload[:1024])
    _put(client, upload_id, 1, payload[1024:])

    tampered = chunk_path(app.state.session_store, session_id, upload_id, 0)
    tampered.write_bytes(b"b" * 1024)  # 大小不变、内容被改动

    response = client.post(f"/api/uploads/{upload_id}/complete")
    assert response.status_code == 409
    assert "校验失败" in response.json()["detail"]

    record = get_upload(app.state.session_store, session_id, upload_id)
    assert record.status == "uploading"
    assert 0 not in record.received  # 坏片被剔除，等待重传
    assert _put(client, upload_id, 0, payload[:1024]).status_code == 200
    assert client.post(f"/api/uploads/{upload_id}/complete").status_code == 200


def test_complete_unknown_upload_404(tmp_path: Path) -> None:
    _, client, _ = _setup(tmp_path)
    assert client.post("/api/uploads/00000000-0000-0000-0000-000000000000/complete").status_code == 404
    assert client.get("/api/uploads/00000000-0000-0000-0000-000000000000").status_code == 404
