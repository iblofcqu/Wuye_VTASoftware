"""任务 3.2：产物登记、列举与下载（原名还原、路径净化、会话隔离）。"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.artifacts import artifact_path, get_artifact, register_artifact, sanitize_name
from app.main import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _setup(tmp_path: Path):
    app = create_app(tmp_path / "sessions")
    client = TestClient(app)
    session_id = client.get("/api/session").json()["session_id"]
    return app, client, session_id


def test_register_list_and_download_restores_name(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    store = app.state.session_store
    source = tmp_path / "source.xyz"
    shutil.copy(FIXTURES / "sample_scene.xyz", source)

    artifact = register_artifact(
        store, session_id, source, name="sub/dir/sample_scene.xyz", kind="pointcloud", source_job="job-1"
    )
    assert artifact.name == "sample_scene.xyz"  # 目录成分被剥离

    listing = client.get("/api/session").json()["artifacts"]
    assert [entry["id"] for entry in listing] == [artifact.id]

    response = client.get(f"/api/artifacts/{artifact.id}/download")
    assert response.status_code == 200
    assert response.content == source.read_bytes()
    assert "sample_scene.xyz" in response.headers["content-disposition"]


def test_non_ascii_download_name_is_rfc5987_encoded(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    source = tmp_path / "source.xyz"
    shutil.copy(FIXTURES / "sample_scene.xyz", source)
    artifact = register_artifact(store=app.state.session_store, session_id=session_id, source_path=source, name="扫描点云.xyz", kind="pointcloud")

    response = client.get(f"/api/artifacts/{artifact.id}/download")
    assert response.status_code == 200
    assert "filename*=utf-8''" in response.headers["content-disposition"]
    assert artifact_path(app.state.session_store, session_id, artifact).name == f"{artifact.id}.xyz"


def test_unknown_artifact_returns_404(tmp_path: Path) -> None:
    _, client, _ = _setup(tmp_path)
    response = client.get("/api/artifacts/00000000-0000-0000-0000-000000000000/download")
    assert response.status_code == 404


def test_cross_session_isolation(tmp_path: Path) -> None:
    app, client_a, session_a = _setup(tmp_path)
    client_b = TestClient(app)
    session_b = client_b.get("/api/session").json()["session_id"]
    assert session_b != session_a

    source = tmp_path / "source.xyz"
    shutil.copy(FIXTURES / "sample_scene.xyz", source)
    artifact = register_artifact(app.state.session_store, session_a, source, name="a.xyz", kind="pointcloud")

    assert client_a.get(f"/api/artifacts/{artifact.id}/download").status_code == 200
    assert client_b.get(f"/api/artifacts/{artifact.id}/download").status_code == 404


def test_tampered_path_is_rejected(tmp_path: Path) -> None:
    app, client, session_id = _setup(tmp_path)
    store = app.state.session_store
    source = tmp_path / "source.xyz"
    shutil.copy(FIXTURES / "sample_scene.xyz", source)
    artifact = register_artifact(store, session_id, source, name="a.xyz", kind="pointcloud")

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    store.update(session_id, lambda record: record.artifacts[0].update({"path": "../../outside.txt"}))

    tampered = get_artifact(store, session_id, artifact.id)
    assert tampered is not None
    with pytest.raises(ValueError):
        artifact_path(store, session_id, tampered)
    assert client.get(f"/api/artifacts/{artifact.id}/download").status_code == 404


@pytest.mark.parametrize("bad", ["", "..", "../", "dir/", "  "])
def test_sanitize_name_rejects_bad_values(bad: str) -> None:
    with pytest.raises(ValueError):
        sanitize_name(bad)


def test_register_rejects_unknown_kind_and_missing_source(tmp_path: Path) -> None:
    app, _, session_id = _setup(tmp_path)
    store = app.state.session_store
    source = tmp_path / "source.xyz"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        register_artifact(store, session_id, source, name="a.xyz", kind="unknown")
    with pytest.raises(FileNotFoundError):
        register_artifact(store, session_id, tmp_path / "missing.xyz", name="a.xyz", kind="pointcloud")
