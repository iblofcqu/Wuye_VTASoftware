"""预览数据：轻量化 + 二进制编码 + 会话内缓存。

二进制格式（小端）：
    MAGIC(4B "WYPV") + version(1B) + header_len(4B uint32)
    + header（UTF-8 JSON：count/source_count/fields/scalar 范围/色带等）
    + positions（Float32，N×3）
    + 可选 scalars（Float32，N）
"""

import json
import os
import struct
from pathlib import Path

import numpy as np

from app import config
from app.core.artifacts import Artifact
from app.core.sessions import SessionStore

PREVIEW_MAGIC = b"WYPV"
PREVIEW_VERSION = 1
PREVIEW_DIR = "previews"
TEXT_SUFFIXES = {".xyz", ".asc", ".txt"}


def load_points(path) -> np.ndarray:
    """读取点云坐标（前三列）。文本格式用 numpy，xls 用 pandas（与基线读取能力一致）。"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        data = np.loadtxt(path)
        points = np.atleast_2d(data)
    elif suffix == ".xls":
        import pandas as pd

        points = pd.read_excel(path, header=None).values
    else:
        raise ValueError(f"暂不支持预览该格式: {suffix or '(无扩展名)'}")
    if points.ndim != 2 or points.shape[1] < 3 or len(points) == 0:
        raise ValueError("点云数据为空或列数不足")
    return np.asarray(points[:, :3], dtype=np.float64)


def decimate_points(
    points: np.ndarray, max_points: int, seed: int = 0
) -> tuple[np.ndarray, np.ndarray | None]:
    """点数超过上限时做确定性随机抽样（仅用于预览，不影响计算数据）。

    返回 (抽样后的点, 索引或 None)；索引同时用于对齐可选的标量。
    """
    if max_points is None or len(points) <= max_points:
        return points, None
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(points), size=max_points, replace=False))
    return points[indices], indices


def encode_preview(
    points: np.ndarray,
    scalars: np.ndarray | None = None,
    *,
    name: str = "",
    max_points: int | None = None,
    scalar_unit: str | None = None,
    colormap: str | None = None,
    extra: dict | None = None,
) -> bytes:
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("预览坐标必须是 N×3")
    if len(points) == 0:
        raise ValueError("点云为空，无法生成预览")

    source_count = len(points)
    points, indices = decimate_points(points, max_points or config.PREVIEW_MAX_POINTS)
    decimated = indices is not None
    if scalars is not None:
        scalars = np.asarray(scalars, dtype=np.float64)
        if len(scalars) != source_count:
            raise ValueError("标量数量与点数不一致")
        if indices is not None:
            scalars = scalars[indices]

    header = {
        "version": PREVIEW_VERSION,
        "count": int(len(points)),
        "source_count": int(source_count),
        "decimated": bool(decimated),
        "fields": ["x", "y", "z"] + (["scalar"] if scalars is not None else []),
        "name": name,
    }
    if scalars is not None:
        header["scalar_min"] = float(np.min(scalars))
        header["scalar_max"] = float(np.max(scalars))
        if scalar_unit is not None:
            header["scalar_unit"] = scalar_unit
        if colormap is not None:
            header["colormap"] = colormap
    if extra:
        header.update(extra)

    payload = np.asarray(points, dtype="<f4").tobytes()
    if scalars is not None:
        payload += np.asarray(scalars, dtype="<f4").tobytes()
    header_bytes = json.dumps(header, ensure_ascii=False).encode("utf-8")
    return PREVIEW_MAGIC + struct.pack("<BI", PREVIEW_VERSION, len(header_bytes)) + header_bytes + payload


def parse_preview_header(data: bytes) -> dict:
    """解析头部（供测试与调试）。"""
    if len(data) < 9 or data[:4] != PREVIEW_MAGIC:
        raise ValueError("非法预览数据")
    version, header_len = struct.unpack("<BI", data[4:9])
    if version != PREVIEW_VERSION:
        raise ValueError(f"不支持的预览版本: {version}")
    header = json.loads(data[9 : 9 + header_len].decode("utf-8"))
    return header


def _cache_path(store: SessionStore, session_id: str, key: str) -> Path:
    return store.session_dir(session_id) / PREVIEW_DIR / f"{key}.bin"


def artifact_preview(
    store: SessionStore,
    session_id: str,
    artifact: Artifact,
    *,
    max_points: int | None = None,
) -> bytes:
    """生成（或复用缓存）产物的预览数据。"""
    cache_path = _cache_path(store, session_id, f"artifact-{artifact.id}")
    if cache_path.exists():
        return cache_path.read_bytes()

    from app.core.artifacts import artifact_path

    points = load_points(artifact_path(store, session_id, artifact))
    data = encode_preview(points, name=artifact.name, max_points=max_points)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_name(cache_path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, cache_path)
    return data


def job_error_preview(store: SessionStore, session_id: str, job: dict) -> bytes:
    """质量评估任务的偏差云预览（按基线显示语义：mm、剔除最大比例置零、seismic）。"""
    cache_path = _cache_path(store, session_id, f"job-{job['id']}")
    if cache_path.exists():
        return cache_path.read_bytes()

    error_cloud = job.get("internal", {}).get("internal_outputs", {}).get("error_cloud")
    if not error_cloud or not Path(error_cloud).is_file():
        raise ValueError("该任务没有可预览的偏差点云")

    data = np.load(error_cloud)
    if data.ndim != 2 or data.shape[1] < 4:
        raise ValueError("偏差云数据格式不正确")
    points = data[:, :3]
    errors_mm = np.asarray(data[:, 3], dtype=np.float64) * 1000.0
    ratio = float(job.get("params", {}).get("ratio", 0.0) or 0.0)
    zero_count = int(len(errors_mm) * ratio)
    if zero_count > 0:
        top = np.argsort(errors_mm)[::-1][:zero_count]
        errors_mm = errors_mm.copy()
        errors_mm[top] = 0.0

    result = job.get("result") or {}
    summary = result.get("summary") or {}
    payload = encode_preview(
        points,
        errors_mm,
        name=f"{summary.get('method', 'QA')}-偏差云",
        scalar_unit="mm",
        colormap="seismic",
        extra={"zeroed_ratio": ratio},
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_name(cache_path.name + ".tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, cache_path)
    return payload
