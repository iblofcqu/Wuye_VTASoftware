"""产物接口：下载（原名还原；路径必须在会话目录内）。"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.artifacts import artifact_path, get_artifact

router = APIRouter()


@router.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str, request: Request) -> FileResponse:
    store = request.app.state.session_store
    session_id = request.state.session_id
    try:
        artifact = get_artifact(store, session_id, artifact_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="会话不存在") from None
    if artifact is None:
        raise HTTPException(status_code=404, detail="产物不存在")

    try:
        path = artifact_path(store, session_id, artifact)
    except ValueError:
        raise HTTPException(status_code=404, detail="产物路径非法") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="产物文件缺失")
    return FileResponse(path, filename=artifact.name)
