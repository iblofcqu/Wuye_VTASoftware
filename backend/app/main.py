"""FastAPI 应用工厂与入口。"""

from pathlib import Path

from fastapi import FastAPI

from app.api.session import install_session_support
from app.config import SESSION_ROOT
from app.core.sessions import SessionStore


def create_app(session_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="DeviScan-3D B/S", version="0.1.0")
    store = SessionStore(session_root or SESSION_ROOT)
    install_session_support(app, store)
    return app


app = create_app()
