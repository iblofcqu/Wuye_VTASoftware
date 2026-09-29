"""服务层公共类型与参数校验工具。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

ProgressCallback = Callable[[str, int, int], None]


def baseline_stem(path) -> str:
    """基线页面的文件名主名规则：按第一个点截断（如 a.b.xyz -> a）。"""
    return Path(path).name.split(".")[0]


def noop_progress(stage: str, done: int, total: int) -> None:
    """默认进度回调（无操作）。"""


def require_positive_number(value, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}必须是数值") from None
    if not np.isfinite(number) or number <= 0:
        raise ValueError(f"{name}必须为正数")
    return number


def require_positive_int(value, name: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}必须是整数") from None
    if not number.is_integer():
        raise ValueError(f"{name}必须是整数")
    if number <= 0:
        raise ValueError(f"{name}必须为正整数")
    return int(number)


@dataclass
class ToolResult:
    output_path: Path
    display_name: str
    summary: dict = field(default_factory=dict)
