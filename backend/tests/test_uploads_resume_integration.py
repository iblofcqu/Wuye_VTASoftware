"""任务 4.4：断点续传集成场景（网络中断续传、页面刷新、服务重启）。"""

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import SESSION_COOKIE_NAME
from app.main import create_app

CHUNK = 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _init(client: TestClient, payload_size: int) -> str:
    response = client.post(
        "/api/uploads", json={"filename": "scan.xyz", "size": payload_size, "chunk_size": CHUNK}
    )
    assert response.status_code == 201, response.text
    return response.json()["upload_id"]


def _put(client: TestClient, upload_id: str, index: int, payload: bytes):
    chunk = payload[index * CHUNK : (index + 1) * CHUNK]
    return client.put(
        f"/api/uploads/{upload_id}/chunks/{index}",
        content=chunk,
        headers={"X-Chunk-SHA256": _sha256(chunk)},
    )


def test_resume_after_interruption_and_refresh(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    client = TestClient(app)
    session_id = client.get("/api/session").json()["session_id"]

    payload = bytes(range(256)) * 16  # 4096 字节 -> 4 个分片
    upload_id = _init(client, len(payload))

    # 网络中断：只成功上传前两个分片
    assert _put(client, upload_id, 0, payload).status_code == 200
    assert _put(client, upload_id, 1, payload).status_code == 200

    # 页面刷新后重新查询：应只缺后两个分片
    status = client.get(f"/api/uploads/{upload_id}").json()
    assert status["received_indices"] == [0, 1]
    assert status["missing_indices"] == [2, 3]

    # 只补缺失分片，不重传已完成部分
    for index in status["missing_indices"]:
        assert _put(client, upload_id, index, payload).status_code == 200

    completed = client.post(f"/api/uploads/{upload_id}/complete")
    assert completed.status_code == 200, completed.text
    artifact = completed.json()["artifact"]
    download = client.get(f"/api/artifacts/{artifact['id']}/download")
    assert download.content == payload
    assert app.state.session_store.load(session_id) is not None


def test_resume_after_server_restart(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    first_app = create_app(root)
    first_client = TestClient(first_app)
    session_id = first_client.get("/api/session").json()["session_id"]

    payload = bytes(reversed(range(256))) * 16
    upload_id = _init(first_client, len(payload))
    assert _put(first_client, upload_id, 0, payload).status_code == 200

    # 模拟服务重启：同数据目录重建应用，浏览器 cookie 保留
    restarted_app = create_app(root)
    restarted_client = TestClient(restarted_app)
    restarted_client.cookies.set(SESSION_COOKIE_NAME, session_id)

    status = restarted_client.get(f"/api/uploads/{upload_id}").json()
    assert status["received_indices"] == [0]
    assert status["missing_indices"] == [1, 2, 3]

    for index in status["missing_indices"]:
        assert _put(restarted_client, upload_id, index, payload).status_code == 200

    completed = restarted_client.post(f"/api/uploads/{upload_id}/complete")
    assert completed.status_code == 200, completed.text
    artifact = completed.json()["artifact"]
    download = restarted_client.get(f"/api/artifacts/{artifact['id']}/download")
    assert download.content == payload
