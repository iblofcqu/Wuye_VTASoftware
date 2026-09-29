"""会话中间件、会话快照与清空 SSE。"""

import asyncio
import json

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from app.core.session_cleanup import (
    CleanupResult,
    SessionCleanupBusy,
    SessionCleanupError,
    SessionCleanupManager,
)
from app.core.sessions import SessionStore, is_valid_session_id


def _sse_event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _active_work_message(record) -> str | None:
    active_jobs = [job for job in record.jobs if job.get("status") in {"queued", "running"}]
    if active_jobs:
        return "当前会话存在排队或运行中的任务，无法清空"
    active_uploads = [
        upload for upload in record.uploads if upload.get("status") in {"uploading", "completing"}
    ]
    if active_uploads:
        return "当前会话存在未完成的上传，无法清空"
    return None


def install_session_support(app: FastAPI, store: SessionStore) -> None:
    @app.middleware("http")
    async def session_middleware(request: Request, call_next):
        cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
        record = store.load(cookie_value) if is_valid_session_id(cookie_value) else None
        if record is None:
            record = store.create()
        request.state.session_id = record.session_id

        response = await call_next(request)
        if cookie_value != record.session_id:
            response.set_cookie(
                SESSION_COOKIE_NAME,
                record.session_id,
                max_age=SESSION_MAX_AGE_SECONDS,
                httponly=True,
                samesite="lax",
            )
        return response

    router = APIRouter()

    @router.get("/api/session")
    def get_session(request: Request) -> dict:
        record = store.load(request.state.session_id)
        assert record is not None
        data = record.to_dict()
        data["artifacts"] = [
            {key: value for key, value in entry.items() if key != "path"} for entry in data["artifacts"]
        ]
        data["uploads"] = [
            {key: value for key, value in entry.items() if key != "chunk_sha256"}
            for entry in data["uploads"]
        ]
        data["jobs"] = [
            {key: value for key, value in entry.items() if key != "internal"} for entry in data["jobs"]
        ]
        return data

    @router.post("/api/session/clear")
    async def clear_session(request: Request) -> StreamingResponse:
        session_id = request.state.session_id
        record = store.load(session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="会话不存在")

        conflict = _active_work_message(record)
        if conflict is not None:
            raise HTTPException(status_code=409, detail=conflict)

        manager: SessionCleanupManager = request.app.state.session_cleanup
        try:
            operation = manager.start(store, session_id)
        except SessionCleanupBusy as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except SessionCleanupError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except Exception as exc:  # noqa: BLE001 - 进程启动失败必须显式返回
            raise HTTPException(
                status_code=500,
                detail=f"清空进程启动失败: {type(exc).__name__}: {exc}",
            ) from None

        async def event_stream():
            yield _sse_event("started", {"state": "started"})
            try:
                result = await asyncio.to_thread(operation.wait)
            except Exception as exc:  # noqa: BLE001 - 等待失败也必须作为流错误返回
                result = CleanupResult(False, f"等待清理进程失败: {type(exc).__name__}: {exc}")
            if result.ok:
                yield _sse_event("success", {"state": "success"})
            else:
                yield _sse_event(
                    "error",
                    {"state": "error", "message": result.message or "清空失败"},
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    app.include_router(router)
