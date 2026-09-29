"""FastAPI 应用工厂与入口。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.artifacts import router as artifacts_router
from app.api.jobs import router as jobs_router
from app.api.session import install_session_support
from app.api.uploads import router as uploads_router
from app.config import SESSION_ROOT
from app.core.sessions import SessionStore
from app.jobs import store as job_store
from app.jobs.runner import JobRunner


def create_app(
    session_root: Path | None = None,
    tool_registry: dict | None = None,
    job_pool_size: int | None = None,
) -> FastAPI:
    store = SessionStore(session_root or SESSION_ROOT)
    runner = JobRunner(store, registry=tool_registry, pool_size=job_pool_size)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        job_store.interrupt_leftover_jobs(store)
        yield
        runner.shutdown()

    app = FastAPI(title="DeviScan-3D B/S", version="0.1.0", lifespan=lifespan)
    app.state.session_store = store
    app.state.job_runner = runner
    install_session_support(app, store)
    app.include_router(artifacts_router)
    app.include_router(uploads_router)
    app.include_router(jobs_router)
    return app


app = create_app()
