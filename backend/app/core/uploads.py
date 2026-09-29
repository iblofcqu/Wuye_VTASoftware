"""断点续传上传：分片幂等接收 + SHA-256 校验 + 合并登记。"""

import hashlib
import hmac
import math
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import config
from app.core.artifacts import register_artifact, sanitize_name
from app.core.sessions import SessionStore, is_valid_session_id, utc_now_iso

UPLOAD_DIR = "uploads"
CHUNK_DIR = "chunks"
MESH_EXTENSIONS = {".stl", ".ply", ".obj", ".off", ".gltf", ".glb"}
POINT_EXTENSIONS = {".xyz", ".asc", ".txt", ".xls"}


class UploadTooLarge(ValueError):
    """文件超过配置的大小上限。"""


class ChecksumMismatch(ValueError):
    """分片或整体校验失败。"""

    def __init__(self, message: str, index: int | None = None):
        super().__init__(message)
        self.index = index


def guess_kind(filename: str) -> str:
    suffix = Path(sanitize_name(filename)).suffix.lower()
    if suffix in MESH_EXTENSIONS:
        return "mesh"
    if suffix in POINT_EXTENSIONS:
        return "pointcloud"
    raise ValueError(f"不支持的文件类型: {suffix or '(无扩展名)'}")


@dataclass
class UploadRecord:
    id: str
    filename: str
    kind: str
    size: int
    chunk_size: int
    received: list = field(default_factory=list)
    chunk_sha256: dict = field(default_factory=dict)
    status: str = "uploading"
    artifact_id: str | None = None
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
            kind=data.get("kind", "pointcloud"),
            size=int(data["size"]),
            chunk_size=int(data["chunk_size"]),
            received=list(data.get("received", [])),
            chunk_sha256=dict(data.get("chunk_sha256", {})),
            status=data.get("status", "uploading"),
            artifact_id=data.get("artifact_id"),
            created_at=data.get("created_at", utc_now_iso()),
            expires_at=data.get("expires_at", ""),
        )


def create_upload(store: SessionStore, session_id: str, filename, size, chunk_size=None) -> UploadRecord:
    name = sanitize_name(filename)
    kind = guess_kind(name)
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

    purge_expired_uploads(store)  # 惰性清理：演示级，无需后台任务

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=config.UPLOAD_TTL_SECONDS)).isoformat(
        timespec="seconds"
    )
    record = UploadRecord(
        id=str(uuid.uuid4()), filename=name, kind=kind, size=size, chunk_size=chunk, expires_at=expires_at
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


def missing_chunks(upload: UploadRecord) -> list[int]:
    received = set(upload.received)
    return [index for index in range(upload.total_chunks) if index not in received]


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
                hashes = dict(entry.get("chunk_sha256", {}))
                hashes[str(index)] = digest
                entry["chunk_sha256"] = hashes
                return
        raise FileNotFoundError(f"上传不存在: {upload_id}")

    store.update(session_id, mark)
    updated = get_upload(store, session_id, upload_id)
    assert updated is not None
    return updated


def _update_upload(store: SessionStore, session_id: str, upload_id: str, mutate) -> None:
    def wrapper(session) -> None:
        for entry in session.uploads:
            if entry.get("id") == upload_id:
                mutate(entry)
                return
        raise FileNotFoundError(f"上传不存在: {upload_id}")

    store.update(session_id, wrapper)


def _assemble(store: SessionStore, session_id: str, upload: UploadRecord) -> tuple[Path, str]:
    missing = missing_chunks(upload)
    if missing:
        raise ValueError(f"存在未上传的分片: {missing}")

    upload_dir = store.session_dir(session_id) / UPLOAD_DIR / upload.id
    assembled = upload_dir / "assembled.bin"
    file_hasher = hashlib.sha256()
    written = 0
    with assembled.open("wb") as out:
        for index in range(upload.total_chunks):
            path = chunk_path(store, session_id, upload.id, index)
            if not path.is_file():
                raise ChecksumMismatch(f"分片文件缺失: {index}", index=index)
            data = path.read_bytes()
            if len(data) != expected_chunk_length(upload, index):
                raise ChecksumMismatch(f"分片长度不符: {index}", index=index)
            digest = hashlib.sha256(data).hexdigest()
            if digest != upload.chunk_sha256.get(str(index), ""):
                raise ChecksumMismatch(f"分片校验失败: {index}", index=index)
            out.write(data)
            file_hasher.update(data)
            written += len(data)
    if written != upload.size:
        raise ChecksumMismatch(f"文件总大小不符：期望 {upload.size}，实际 {written}")
    return assembled, file_hasher.hexdigest()


def complete_upload(store: SessionStore, session_id: str, upload_id: str):
    """合并分片并登记产物；completed 状态下幂等返回既有产物。"""
    upload = get_upload(store, session_id, upload_id)
    if upload is None:
        raise FileNotFoundError(f"上传不存在: {upload_id}")
    if upload.status == "completed" and upload.artifact_id:
        return upload, upload.artifact_id
    if upload.status != "uploading":
        raise ValueError(f"上传状态不可完成: {upload.status}")

    def claim(entry) -> None:
        if entry.get("status") != "uploading":
            raise ValueError(f"上传状态不可完成: {entry.get('status')}")
        entry["status"] = "completing"

    _update_upload(store, session_id, upload_id, claim)

    try:
        assembled, _file_sha256 = _assemble(store, session_id, upload)
    except (ValueError, ChecksumMismatch) as exc:
        def recover(entry) -> None:
            entry["status"] = "uploading"
            if isinstance(exc, ChecksumMismatch) and exc.index is not None:
                received = set(entry.get("received", []))
                received.discard(exc.index)
                entry["received"] = sorted(received)
                hashes = dict(entry.get("chunk_sha256", {}))
                hashes.pop(str(exc.index), None)
                entry["chunk_sha256"] = hashes
                chunk_path(store, session_id, upload_id, exc.index).unlink(missing_ok=True)

        _update_upload(store, session_id, upload_id, recover)
        raise

    artifact = register_artifact(
        store, session_id, assembled, name=upload.filename, kind=upload.kind, move=True
    )
    shutil.rmtree(store.session_dir(session_id) / UPLOAD_DIR / upload_id, ignore_errors=True)

    def finalize(entry) -> None:
        entry["status"] = "completed"
        entry["artifact_id"] = artifact.id

    _update_upload(store, session_id, upload_id, finalize)
    updated = get_upload(store, session_id, upload_id)
    assert updated is not None
    return updated, artifact.id


def cancel_upload(store: SessionStore, session_id: str, upload_id: str) -> UploadRecord:
    upload = get_upload(store, session_id, upload_id)
    if upload is None:
        raise FileNotFoundError(f"上传不存在: {upload_id}")
    if upload.status == "completed":
        raise ValueError("已完成的上传不能取消")
    if upload.status == "completing":
        raise ValueError("上传正在合并，无法取消")
    if upload.status == "aborted":  # 幂等
        return upload

    _update_upload(store, session_id, upload_id, lambda entry: entry.update({"status": "aborted"}))
    shutil.rmtree(store.session_dir(session_id) / UPLOAD_DIR / upload_id, ignore_errors=True)
    updated = get_upload(store, session_id, upload_id)
    assert updated is not None
    return updated


def purge_expired_uploads(store: SessionStore, now=None) -> list[str]:
    """清理超过保留期限的未完成上传（含崩溃遗留的 completing），返回被清理的 upload id。"""
    now = now or datetime.now(timezone.utc)
    purged: list[str] = []
    if not store.root.exists():
        return purged
    for session_dir in sorted(store.root.iterdir()):
        session_id = session_dir.name
        if not session_dir.is_dir() or not is_valid_session_id(session_id):
            continue
        record = store.load(session_id)
        if record is None:
            continue
        for entry in list(record.uploads):
            if entry.get("status") in {"completed", "aborted"}:
                continue
            expires_at = entry.get("expires_at")
            if not expires_at:
                continue
            try:
                deadline = datetime.fromisoformat(expires_at)
            except ValueError:
                continue
            if deadline > now:
                continue
            upload_id = entry["id"]
            _update_upload(
                store, session_id, upload_id, lambda item: item.update({"status": "aborted"})
            )
            shutil.rmtree(store.session_dir(session_id) / UPLOAD_DIR / upload_id, ignore_errors=True)
            purged.append(upload_id)
    return purged
