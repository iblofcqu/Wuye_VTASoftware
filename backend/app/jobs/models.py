"""任务记录模型与状态。"""

import uuid
from dataclasses import asdict, dataclass, field

from app.core.sessions import utc_now_iso

JOB_STATUSES = {"queued", "running", "succeeded", "failed", "interrupted"}


@dataclass
class JobRecord:
    id: str
    tool: str
    status: str = "queued"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    error: str | None = None
    result: dict | None = None
    internal: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "JobRecord":
        return cls(
            id=data["id"],
            tool=data["tool"],
            status=data.get("status", "queued"),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
            error=data.get("error"),
            result=data.get("result"),
            internal=dict(data.get("internal", {})),
        )


def new_job(tool: str) -> JobRecord:
    return JobRecord(id=str(uuid.uuid4()), tool=tool)
