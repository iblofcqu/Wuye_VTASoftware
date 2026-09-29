"""预览接口：产物点云预览与任务偏差云预览。"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.artifacts import artifact_path, get_artifact
from app.core.preview import artifact_preview, job_error_preview
from app.jobs import store as job_store

router = APIRouter()


@router.get("/api/artifacts/{artifact_id}/preview")
def get_artifact_preview(artifact_id: str, request: Request) -> Response:
    store = request.app.state.session_store
    session_id = request.state.session_id
    artifact = get_artifact(store, session_id, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="产物不存在")
    if artifact.kind != "pointcloud":
        raise HTTPException(status_code=400, detail="该产物类型不支持点云预览")
    try:
        path = artifact_path(store, session_id, artifact)
    except ValueError:
        raise HTTPException(status_code=422, detail="产物路径非法，无法预览") from None
    if not path.is_file():
        raise HTTPException(status_code=422, detail="产物文件缺失，无法预览")
    try:
        data = artifact_preview(store, session_id, artifact)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"预览生成失败: {exc}") from None
    return Response(content=data, media_type="application/octet-stream")


@router.get("/api/jobs/{job_id}/preview")
def get_job_preview(job_id: str, request: Request) -> Response:
    store = request.app.state.session_store
    session_id = request.state.session_id
    job = job_store.get_job(store, session_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.get("status") != "succeeded":
        raise HTTPException(status_code=409, detail="任务尚未成功完成，暂无可预览结果")
    try:
        data = job_error_preview(store, session_id, job)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=f"预览生成失败: {exc}") from None
    return Response(content=data, media_type="application/octet-stream")
