"""用于报告超时测试的顶层目标和工具函数。"""

import time
from pathlib import Path

from app.report import supervisor


def quick_report_target(*, progress, report_progress, **kwargs):
    report_progress("快速阶段")
    progress("第4/4步 测试", 4, 4)
    return {"ok": True}


def blocking_report_target(*, progress, report_progress, **kwargs):
    report_progress("阻塞阶段")
    while True:
        time.sleep(0.05)


def supervised_report_tool(params, inputs, input_names, work_dir, progress):
    target = blocking_report_target if params.get("mode") == "blocking" else quick_report_target
    result = supervisor.run_report_phase(
        target,
        work_dir=Path(work_dir),
        timeout_seconds=int(params["timeout_seconds"]),
    )
    return {"outputs": [], "summary": result, "internal_outputs": {}}
