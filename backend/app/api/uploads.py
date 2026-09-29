"""上传接口：初始化与分片接收（断点续传的基础）。"""

import hashlib

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.artifacts import artifact_public_dict, get_artifact
from app.core.uploads import (
    ChecksumMismatch,
    UploadTooLarge,
    cancel_upload,
    complete_upload,
    create_upload,
    expected_chunk_length,
    get_upload,
    missing_chunks,
    receive_chunk,
)

router = APIRouter()


class UploadInitRequest(BaseModel):
    filename: str
    size: int
    chunk_size: int | None = None


def _progress(upload) -> dict:
    return {
        "upload_id": upload.id,
        "filename": upload.filename,
        "kind": upload.kind,
        "size": upload.size,
        "chunk_size": upload.chunk_size,
        "total_chunks": upload.total_chunks,
        "received": len(upload.received),
        "received_indices": upload.received,
        "missing_indices": missing_chunks(upload),
        "status": upload.status,
        "expires_at": upload.expires_at,
        "artifact_id": upload.artifact_id,
    }


@router.post("/api/uploads", status_code=201)
def init_upload(payload: UploadInitRequest, request: Request) -> dict:
    store = request.app.state.session_store
    try:
        upload = create_upload(
            store, request.state.session_id, payload.filename, payload.size, payload.chunk_size
        )
    except UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _progress(upload)


@router.put("/api/uploads/{upload_id}/chunks/{index}")
async def put_chunk(upload_id: str, index: int, request: Request) -> dict:
    store = request.app.state.session_store
    session_id = request.state.session_id
    upload = get_upload(store, session_id, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="上传不存在")
    if index in upload.received:  # 幂等
        return _progress(upload)
    try:
        expected = expected_chunk_length(upload, index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    checksum = request.headers.get("x-chunk-sha256", "")
    if len(checksum) != 64:
        raise HTTPException(status_code=400, detail="缺少或非法 X-Chunk-SHA256 头")

    collected = bytearray()
    hasher = hashlib.sha256()
    async for piece in request.stream():
        hasher.update(piece)
        collected.extend(piece)
        if len(collected) > expected:
            raise HTTPException(status_code=413, detail=f"分片长度超出预期（{expected} 字节）")
    if len(collected) != expected:
        raise HTTPException(status_code=400, detail=f"分片长度不符：期望 {expected} 字节")
    if hasher.hexdigest() != checksum.lower():
        raise HTTPException(status_code=400, detail="分片校验失败")

    try:
        updated = receive_chunk(store, session_id, upload_id, index, bytes(collected), checksum)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ChecksumMismatch as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _progress(updated)


@router.get("/api/uploads/{upload_id}")
def get_upload_status(upload_id: str, request: Request) -> dict:
    upload = get_upload(request.app.state.session_store, request.state.session_id, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="上传不存在")
    return _progress(upload)


@router.post("/api/uploads/{upload_id}/complete")
def finish_upload(upload_id: str, request: Request) -> dict:
    store = request.app.state.session_store
    session_id = request.state.session_id
    try:
        upload, artifact_id = complete_upload(store, session_id, upload_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ChecksumMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None

    artifact = get_artifact(store, session_id, artifact_id)
    assert artifact is not None
    progress = _progress(upload)
    progress["artifact"] = artifact_public_dict(artifact)
    return progress


@router.delete("/api/uploads/{upload_id}")
def cancel(upload_id: str, request: Request) -> dict:
    try:
        upload = cancel_upload(request.app.state.session_store, request.state.session_id, upload_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _progress(upload)
