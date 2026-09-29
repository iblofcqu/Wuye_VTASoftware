"""任务 6.2：预览接口（点云产物 + 偏差云标量/色带编码）。"""

import struct
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.core.artifacts import register_artifact
from app.core.preview import PREVIEW_MAGIC, parse_preview_header
from app.core.sessions import SessionStore
from app.jobs.models import new_job
from app.jobs.store import add_job
from app.main import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _decode(data: bytes) -> tuple[dict, np.ndarray, np.ndarray | None]:
    header = parse_preview_header(data)
    header_len = struct.unpack("<I", data[5:9])[0]
    floats = np.frombuffer(data[9 + header_len :], dtype="<f4")
    count = header["count"]
    points = floats[: count * 3].reshape(-1, 3)
    scalars = floats[count * 3 :] if "scalar" in header["fields"] else None
    return header, points, scalars


def test_artifact_preview_endpoint_and_cache(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        artifact = register_artifact(
            store, session_id, FIXTURES / "sample_scene.xyz", name="sample_scene.xyz", kind="pointcloud"
        )

        first = client.get(f"/api/artifacts/{artifact.id}/preview")
        assert first.status_code == 200, first.text
        assert first.content[:4] == PREVIEW_MAGIC
        header, points, scalars = _decode(first.content)
        assert header["count"] == 600 and header["name"] == "sample_scene.xyz"
        assert scalars is None and points.shape == (600, 3)

        second = client.get(f"/api/artifacts/{artifact.id}/preview")
        assert second.content == first.content  # 缓存命中


def test_preview_rejects_non_pointcloud_and_unknown(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        mesh_file = tmp_path / "mesh.stl"
        mesh_file.write_text("solid", encoding="utf-8")
        mesh = register_artifact(store, session_id, mesh_file, name="mesh.stl", kind="mesh")

        response = client.get(f"/api/artifacts/{mesh.id}/preview")
        assert response.status_code == 400 and "不支持" in response.json()["detail"]
        assert client.get("/api/artifacts/00000000-0000-0000-0000-000000000000/preview").status_code == 404


def test_job_error_cloud_preview_zeroes_top_ratio(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]

        points = np.column_stack([np.arange(100.0), np.zeros(100), np.zeros(100)])
        errors_m = np.linspace(0.001, 0.100, 100)  # 1~100mm
        error_cloud = tmp_path / "error_cloud.npy"
        np.save(error_cloud, np.column_stack([points, errors_m]))

        job = new_job("quality-assess", {"ratio": 0.1})
        job.status = "succeeded"
        job.internal = {"internal_outputs": {"error_cloud": str(error_cloud)}}
        add_job(store, session_id, job)

        response = client.get(f"/api/jobs/{job.id}/preview")
        assert response.status_code == 200, response.text
        header, decoded_points, scalars = _decode(response.content)
        assert header["fields"] == ["x", "y", "z", "scalar"]
        assert header["scalar_unit"] == "mm" and header["colormap"] == "seismic"
        assert header["zeroed_ratio"] == 0.1

        assert np.all(scalars[:90] > 0)  # 未剔除部分保留 mm 值
        assert np.all(scalars[90:] == 0)  # 最大的 10% 被置零（基线语义）


def test_job_preview_requires_success_and_known_job(tmp_path: Path) -> None:
    app = create_app(tmp_path / "sessions")
    store = app.state.session_store
    with TestClient(app) as client:
        session_id = client.get("/api/session").json()["session_id"]
        running = new_job("quality-assess", {"ratio": 0.1})
        running.status = "running"
        add_job(store, session_id, running)

        assert client.get(f"/api/jobs/{running.id}/preview").status_code == 409
        assert client.get("/api/jobs/00000000-0000-0000-0000-000000000000/preview").status_code == 404
