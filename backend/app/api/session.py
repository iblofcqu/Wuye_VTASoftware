"""会话中间件与 GET /api/session。"""

from fastapi import APIRouter, FastAPI, Request

from app.config import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from app.core.sessions import SessionStore, is_valid_session_id


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
        return record.to_dict()

    app.include_router(router)
