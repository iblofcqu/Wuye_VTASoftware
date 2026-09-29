"""断点续传上传：分片幂等接收 + SHA-256 校验。"""

import hashlib
import hmac
import math
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import config
from app.core.artifacts import sanitize_name
from app.core.sessions import SessionStore, utc_now_iso

UPLOAD_DIR = "uploads"
CHUNK_DIR = "chunks"


class UploadTooLarge(ValueError):
    """文件超过配置的大小上限。"""


class ChecksumMismatch(ValueError):
    """分片校验失败。"""


@dataclass
class UploadRecord:
    id: str
    filename: str
    size: int
    chunk_size: int
    received: list = field(default_factory=list)
    status: str = "uploading"
    created_at: str = field(default_factory=utc_now_iso)
    expires_at: str = ""

    @property
    def total_chunks(self) -> int:
        return math.ceil(self.size / self.chunk_size)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UploadRecord":
        return cls(
            id=data["id"],
            filename=data["filename"],
            size=int(data["size"]),
            chunk_size=int(data["chunk_size"]),
            received=list(data.get("received", [])),
            status=data.get("status", "uploading"),
            created_at=data.get("created_at", utc_now_iso()),
            expires_at=data.get("expires_at", ""),
        )


def create_upload(store: SessionStore, session_id: str, filename, size, chunk_size=None) -> UploadRecord:
    name = sanitize_name(filename)
    try:
        size = int(size)
    except (TypeError, ValueError):
        raise ValueError("文件大小必须是整数") from None
    if size <= 0:
        raise ValueError("文件大小必须为正数")
    if size > config.MAX_UPLOAD_BYTES:
        raise UploadTooLarge(f"文件超过大小上限（{config.MAX_UPLOAD_BYTES} 字节）")
    chunk = int(chunk_size) if chunk_size is not None else config.UPLOAD_CHUNK_SIZE
    if chunk < config.UPLOAD_MIN_CHUNK_SIZE or chunk > config.UPLOAD_MAX_CHUNK_SIZE:
        raise ValueError(
            f"分片大小必须在 {config.UPLOAD_MIN_CHUNK_SIZE}~{config.UPLOAD_MAX_CHUNK_SIZE} 字节之间"
        )
    if store.load(session_id) is None:
        raise FileNotFoundError(f"会话不存在: {session_id}")

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=config.UPLOAD_TTL_SECONDS)).isoformat(
        timespec="seconds"
    )
    record = UploadRecord(
        id=str(uuid.uuid4()), filename=name, size=size, chunk_size=chunk, expires_at=expires_at
    )
    store.update(session_id, lambda session: session.uploads.append(record.to_dict()))
    return record


def get_upload(store: SessionStore, session_id: str, upload_id: str) -> UploadRecord | None:
    session = store.load(session_id)
    if session is None:
        return None
    for entry in session.uploads:
        if entry.get("id") == upload_id:
            return UploadRecord.from_dict(entry)
    return None


def chunk_path(store: SessionStore, session_id: str, upload_id: str, index: int) -> Path:
    return store.session_dir(session_id) / UPLOAD_DIR / upload_id / CHUNK_DIR / f"{index}.part"


def expected_chunk_length(upload: UploadRecord, index: int) -> int:
    if index < 0 or index >= upload.total_chunks:
        raise ValueError(f"分片序号超出范围: {index}")
    start = index * upload.chunk_size
    return min(upload.chunk_size, upload.size - start)


def receive_chunk(
    store: SessionStore, session_id: str, upload_id: str, index: int, data: bytes, checksum: str
) -> UploadRecord:
    upload = get_upload(store, session_id, upload_id)
    if upload is None:
        raise FileNotFoundError(f"上传不存在: {upload_id}")
    if upload.status != "uploading":
        raise ValueError(f"上传状态不可写: {upload.status}")
    length = expected_chunk_length(upload, index)
    if index in upload.received:  # 幂等：重复提交直接返回当前进度
        return upload
    if not isinstance(checksum, str) or len(checksum) != 64:
        raise ValueError("分片校验值格式错误（需要 SHA-256 十六进制）")
    digest = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(digest, checksum.lower()):
        raise ChecksumMismatch("分片校验失败")
    if len(data) != length:
        raise ValueError(f"分片长度不符：期望 {length} 字节，收到 {len(data)} 字节")

    path = chunk_path(store, session_id, upload_id, index)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, path)

    def mark(session) -> None:
        for entry in session.uploads:
            if entry.get("id") == upload_id:
                received = set(entry.get("received", []))
                received.add(index)
                entry["received"] = sorted(received)
                return
        raise FileNotFoundError(f"上传不存在: {upload_id}")

    store.update(session_id, mark)
    updated = get_upload(store, session_id, upload_id)
    assert updated is not None
    return updated
