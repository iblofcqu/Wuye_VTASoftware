"""健康检查接口：部署依赖自检。"""

from fastapi import APIRouter

from app.core.health import run_health_checks

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    checks = run_health_checks()
    ok = all(check["ok"] for check in checks)
    return {"status": "ok" if ok else "degraded", "checks": checks}
