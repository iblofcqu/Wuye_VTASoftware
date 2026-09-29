"""任务 6.1：预览数据生成、轻量化与缓存。"""

import struct
from pathlib import Path

import numpy as np

from app.core.artifacts import register_artifact
from app.core.preview import (
    PREVIEW_MAGIC,
    PREVIEW_VERSION,
    artifact_preview,
    encode_preview,
    parse_preview_header,
)
from app.core.sessions import SessionStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_encode_preview_header_and_payload() -> None:
    points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    data = encode_preview(points, name="sample.xyz")
    header = parse_preview_header(data)

    assert data[:4] == PREVIEW_MAGIC
    assert struct.unpack("<B", data[4:5])[0] == PREVIEW_VERSION
    assert header["count"] == 2 and header["source_count"] == 2 and not header["decimated"]
    assert header["fields"] == ["x", "y", "z"]
    assert header["name"] == "sample.xyz"

    header_len = struct.unpack("<I", data[5:9])[0]
    payload = data[9 + header_len :]
    positions = np.frombuffer(payload, dtype="<f4").reshape(-1, 3)
    assert np.allclose(positions, points.astype("float32"))


def test_default_cap_limits_points() -> None:
    rng = np.random.default_rng(0)
    points = rng.random((1_200_000, 3), dtype=np.float32)
    data = encode_preview(points)
    header = parse_preview_header(data)

    assert header["count"] == 1_000_000
    assert header["source_count"] == 1_200_000
    assert header["decimated"] is True
    positions_len = header["count"] * 3 * 4
    assert len(data) == 9 + len(data[9 : 9 + struct.unpack("<I", data[5:9])[0]]) + positions_len


def test_scalar_preview_metadata() -> None:
    points = np.zeros((4, 3))
    scalars = np.array([0.0, 1.0, 2.5, 3.0])
    header = parse_preview_header(
        encode_preview(points, scalars, name="err", scalar_unit="mm", colormap="seismic")
    )
    assert header["fields"] == ["x", "y", "z", "scalar"]
    assert header["scalar_min"] == 0.0 and header["scalar_max"] == 3.0
    assert header["scalar_unit"] == "mm" and header["colormap"] == "seismic"


def test_artifact_preview_is_cached(tmp_path: Path, monkeypatch) -> None:
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    artifact = register_artifact(
        store, session.session_id, FIXTURES / "sample_scene.xyz", name="sample_scene.xyz", kind="pointcloud"
    )

    first = artifact_preview(store, session.session_id, artifact)
    assert parse_preview_header(first)["count"] == 600

    from app.core import preview as preview_module

    def fail(*args, **kwargs):
        raise AssertionError("缓存命中时不应重新生成")

    monkeypatch.setattr(preview_module, "load_points", fail)
    second = artifact_preview(store, session.session_id, artifact)
    assert second == first


def test_preview_decimation_keeps_cap(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    large = rng.random((5000, 3))
    data = encode_preview(large, max_points=1000)
    header = parse_preview_header(data)
    assert header["count"] == 1000 and header["decimated"] is True


def test_scalars_stay_aligned_when_decimated() -> None:
    rng = np.random.default_rng(3)
    points = rng.random((5000, 3))
    scalars = points[:, 0] * 1000.0

    data = encode_preview(points, scalars, max_points=800)
    header = parse_preview_header(data)
    header_len = struct.unpack("<I", data[5:9])[0]
    payload = data[9 + header_len :]
    floats = np.frombuffer(payload, dtype="<f4")
    count = header["count"]
    positions = floats[: count * 3].reshape(-1, 3)
    decoded_scalars = floats[count * 3 :]
    assert count == 800
    assert np.allclose(decoded_scalars, positions[:, 0] * 1000.0, rtol=1e-5)
