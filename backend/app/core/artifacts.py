"""产物登记与访问：内部按 artifact id 存文件，下载时还原原命名。"""

import os
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.sessions import SessionStore, utc_now_iso

ARTIFACT_KINDS = {"mesh", "pointcloud", "report"}
ARTIFACT_DIR = "artifacts"


@dataclass
class Artifact:
    id: str
    name: str
    kind: str
    size: int
    created_at: str
    source_job: str | None = None
    path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Artifact":
        return cls(
            id=data["id"],
            name=data["name"],
            kind=data["kind"],
            size=int(data.get("size", 0)),
            created_at=data.get("created_at", utc_now_iso()),
            source_job=data.get("source_job"),
            path=data.get("path", ""),
        )


def sanitize_name(name) -> str:
    """去掉任何目录成分，拒绝空名、纯父目录引用与目录式名称（以分隔符结尾）。"""
    raw = str(name).replace("\\", "/")
    if raw.endswith("/"):
        raise ValueError(f"非法产物文件名: {name!r}")
    candidate = Path(raw).name.strip()
    if candidate in {"", ".", ".."}:
        raise ValueError(f"非法产物文件名: {name!r}")
    return candidate


def register_artifact(
    store: SessionStore,
    session_id: str,
    source_path,
    *,
    name: str,
    kind: str,
    source_job: str | None = None,
) -> Artifact:
    if kind not in ARTIFACT_KINDS:
        raise ValueError(f"未知产物类型: {kind}")
    display_name = sanitize_name(name)
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"产物源文件不存在: {source}")
    if store.load(session_id) is None:
        raise FileNotFoundError(f"会话不存在: {session_id}")

    artifact_id = str(uuid.uuid4())
    suffix = Path(display_name).suffix
    relative = Path(ARTIFACT_DIR) / f"{artifact_id}{suffix}"
    destination = store.session_dir(session_id) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

    artifact = Artifact(
        id=artifact_id,
        name=display_name,
        kind=kind,
        size=destination.stat().st_size,
        created_at=utc_now_iso(),
        source_job=source_job,
        path=str(relative).replace(os.sep, "/"),
    )
    store.update(session_id, lambda record: record.artifacts.append(artifact.to_dict()))
    return artifact


def list_artifacts(store: SessionStore, session_id: str) -> list[dict]:
    record = store.load(session_id)
    if record is None:
        raise FileNotFoundError(f"会话不存在: {session_id}")
    return list(record.artifacts)


def get_artifact(store: SessionStore, session_id: str, artifact_id: str) -> Artifact | None:
    for entry in list_artifacts(store, session_id):
        if entry.get("id") == artifact_id:
            return Artifact.from_dict(entry)
    return None


def artifact_path(store: SessionStore, session_id: str, artifact: Artifact) -> Path:
    """解析产物文件路径，并确保其位于会话目录内。"""
    base = store.session_dir(session_id).resolve()
    candidate = (base / artifact.path).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"非法产物路径: {artifact.path!r}")
    return candidate
