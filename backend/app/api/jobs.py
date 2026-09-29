"""任务接口：提交与查询。"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.artifacts import artifact_path, get_artifact
from app.jobs.tools import INPUT_SPECS

router = APIRouter()


class JobSubmitRequest(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)


@router.post("/api/tools/{tool}/jobs", status_code=202)
def submit_job(tool: str, payload: JobSubmitRequest, request: Request) -> dict:
    runner = request.app.state.job_runner
    store = request.app.state.session_store
    session_id = request.state.session_id
    if tool not in runner.registry:
        raise HTTPException(status_code=404, detail=f"未知工具: {tool}")

    required = INPUT_SPECS.get(tool, ())
    missing = [key for key in required if key not in payload.inputs]
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少输入: {missing}")

    input_paths: dict[str, str] = {}
    input_names: dict[str, str] = {}
    for key, artifact_id in payload.inputs.items():
        artifact = get_artifact(store, session_id, artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail=f"输入产物不存在: {key}")
        path = artifact_path(store, session_id, artifact)
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"输入产物文件缺失: {key}")
        input_paths[key] = str(path)
        input_names[key] = artifact.name

    return runner.submit(session_id, tool, payload.params, input_paths, input_names)


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict:
    view = request.app.state.job_runner.view_job(request.state.session_id, job_id)
    if view is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return view
