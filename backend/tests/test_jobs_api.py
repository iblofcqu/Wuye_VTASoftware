"""任务 5.4：任务接口的成功、失败与池满排队（含真实工具与结果载荷）。"""

import time
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.core.artifacts import register_artifact
from app.main import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def slow_tool(params, inputs, input_names, work_dir, progress):
    time.sleep(float(params.get("seconds", 1.0)))
    output = Path(work_dir) / "out.xyz"
    output.write_text("data", encoding="utf-8")
    return {
        "outputs": [{"path": str(output), "display_name": "out.xyz", "kind": "pointcloud"}],
        "summary": {},
        "internal_outputs": {},
    }


def _poll(client: TestClient, job_id: str, predicate, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        view = client.get(f"/api/jobs/{job_id}").json()
        if predicate(view):
            return view
        time.sleep(0.1)
    raise AssertionError(f"等待超时: {client.get(f'/api/jobs/{job_id}').json()}")


def test_real_tool_success_registers_downloadable_artifact(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        source = register_artifact(
            store, session_id, FIXTURES / "sample_scene.xyz", name="sample_scene.xyz", kind="pointcloud"
        )

        response = client.post(
            "/api/tools/downsample-voxel/jobs",
            json={"inputs": {"input": source.id}, "params": {"voxel_size": 0.1}},
        )
        assert response.status_code == 202, response.text
        job_id = response.json()["id"]

        final = _poll(client, job_id, lambda v: v["status"] in {"succeeded", "failed"})
        assert final["status"] == "succeeded", final.get("error")

        artifact = final["result"]["artifacts"][0]
        assert artifact["name"] == "sample_scene_VD.xyz"
        assert final["result"]["summary"]["point_count"] > 0
        assert final["result"]["summary"]["input_point_count"] == 600

        download = client.get(f"/api/artifacts/{artifact['id']}/download")
        assert download.status_code == 200
        assert len(np.loadtxt(download.text.splitlines())) == final["result"]["summary"]["point_count"]


def test_bad_params_fail_with_reason_and_no_new_artifact(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        source = register_artifact(
            store, session_id, FIXTURES / "sample_scene.xyz", name="sample_scene.xyz", kind="pointcloud"
        )

        response = client.post(
            "/api/tools/downsample-voxel/jobs",
            json={"inputs": {"input": source.id}, "params": {"voxel_size": 0}},
        )
        assert response.status_code == 202
        final = _poll(client, response.json()["id"], lambda v: v["status"] == "failed")
        assert "体素尺寸" in final["error"]
        assert final["result"] is None
        assert len(store.load(session_id).artifacts) == 1  # 只有输入产物


def test_pool_capacity_shows_queued_via_api(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions", tool_registry={"slow": slow_tool}, job_pool_size=1)
    with TestClient(app) as client:
        client.get("/api/session")
        first = client.post("/api/tools/slow/jobs", json={"inputs": {}, "params": {"seconds": 1.5}}).json()
        second = client.post("/api/tools/slow/jobs", json={"inputs": {}, "params": {"seconds": 0.1}}).json()

        deadline = time.time() + 10
        observed = False
        while time.time() < deadline:
            first_view = client.get(f"/api/jobs/{first['id']}").json()
            second_view = client.get(f"/api/jobs/{second['id']}").json()
            if first_view["status"] == "running" and second_view["status"] == "queued":
                observed = True
                break
            time.sleep(0.02)
        assert observed, "未观察到 running + queued"

        _poll(client, first["id"], lambda v: v["status"] == "succeeded")
        _poll(client, second["id"], lambda v: v["status"] == "succeeded")


def test_submit_validation(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    with TestClient(app) as client:
        client.get("/api/session")
        assert client.post("/api/tools/unknown/jobs", json={"inputs": {}, "params": {}}).status_code == 404
        missing = client.post("/api/tools/downsample-voxel/jobs", json={"inputs": {}, "params": {}})
        assert missing.status_code == 400 and "缺少输入" in missing.json()["detail"]
        unknown_artifact = client.post(
            "/api/tools/downsample-voxel/jobs",
            json={"inputs": {"input": "00000000-0000-0000-0000-000000000000"}, "params": {}},
        )
        assert unknown_artifact.status_code == 404
