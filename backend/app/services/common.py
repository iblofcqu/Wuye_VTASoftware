"""服务层公共类型：进度回调与工具执行结果。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[str, int, int], None]


def baseline_stem(path) -> str:
    """基线页面的文件名主名规则：按第一个点截断（如 a.b.xyz -> a）。"""
    return Path(path).name.split(".")[0]


def noop_progress(stage: str, done: int, total: int) -> None:
    """默认进度回调（无操作）。"""


@dataclass
class ToolResult:
    output_path: Path
    display_name: str
    summary: dict = field(default_factory=dict)
