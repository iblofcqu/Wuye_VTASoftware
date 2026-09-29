"""在独立子进程中执行报告阶段，并在超时后终止完整进程树。"""

import json
import os
import pickle
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPORT_STATE_FILE = "report_state.json"
REPORT_PAYLOAD_FILE = "report_payload.pkl"
REPORT_RESULT_FILE = "report_result.json"
REPORT_LOG_FILE = "report_process.log"
_POLL_INTERVAL_SECONDS = 0.1
_TERMINATE_WAIT_SECONDS = 10.0


class ReportTimeoutError(TimeoutError):
    """报告阶段超过配置时限。"""

    def __init__(self, timeout_seconds: int, stage: str | None):
        self.timeout_seconds = int(timeout_seconds)
        self.stage = stage or "未知报告阶段"
        super().__init__(
            f"报告生成超时（{self.timeout_seconds} 秒），最后阶段：{self.stage}"
        )

    def __reduce__(self):
        return (type(self), (self.timeout_seconds, self.stage))


class ReportChildError(RuntimeError):
    """报告子进程异常退出或未返回有效结果。"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def write_report_stage(state_path: Path, stage: str) -> None:
    """记录报告阶段已开始及最后进入的子阶段。"""
    _atomic_write_json(
        Path(state_path),
        {
            "report_started": True,
            "stage": str(stage),
            "updated_at": _utc_now_iso(),
        },
    )


def write_progress(work_dir: Path, stage: str, done: int, total: int) -> None:
    """在报告子进程中写入与任务 runner 兼容的 progress.json。"""
    _atomic_write_json(
        Path(work_dir) / "progress.json",
        {
            "stage": stage,
            "done": int(done),
            "total": int(total),
            "updated_at": _utc_now_iso(),
        },
    )


def read_report_state(state_path: Path) -> dict | None:
    try:
        return json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def terminate_process_tree(pid: int) -> None:
    """尽力终止报告子进程及其后代进程。"""
    if pid <= 0:
        return

    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_TERMINATE_WAIT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        return

    try:
        process_group = os.getpgid(pid)
        os.killpg(process_group, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _load_result(result_path: Path) -> Any:
    if not result_path.is_file():
        raise ReportChildError("报告子进程未返回结果")
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportChildError(f"报告子进程结果无法解析: {exc}") from None
    if payload.get("ok"):
        return payload.get("result")
    error = payload.get("error") or {}
    raise ReportChildError(
        f"{error.get('type', 'ReportChildError')}: {error.get('message', '报告子进程失败')}"
    )


def _popen_kwargs() -> dict:
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}


def run_report_phase(
    target: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    *,
    work_dir: Path,
    timeout_seconds: int,
) -> Any:
    """执行报告阶段；超时后终止子进程树并抛出 ReportTimeoutError。"""
    timeout_seconds = int(timeout_seconds)
    if timeout_seconds <= 0:
        raise ValueError("报告超时时间必须为正数")

    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)
    state_path = work_path / REPORT_STATE_FILE
    payload_path = work_path / REPORT_PAYLOAD_FILE
    result_path = work_path / REPORT_RESULT_FILE
    log_path = work_path / REPORT_LOG_FILE

    state_path.unlink(missing_ok=True)
    result_path.unlink(missing_ok=True)
    payload_path.write_bytes(
        pickle.dumps(
            {
                "target": target,
                "args": tuple(args),
                "kwargs": dict(kwargs or {}),
                "work_dir": str(work_path),
                "state_path": str(state_path),
            },
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    )

    command = [
        sys.executable,
        "-m",
        "app.report.worker",
        str(payload_path),
        str(result_path),
    ]
    backend_dir = Path(__file__).resolve().parents[2]

    report_started_at: float | None = None
    last_stage: str | None = None
    process: subprocess.Popen | None = None

    try:
        with log_path.open("ab") as log_file:
            process = subprocess.Popen(
                command,
                cwd=backend_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                **_popen_kwargs(),
            )

            while process.poll() is None:
                state = read_report_state(state_path)
                if state and state.get("report_started"):
                    report_started_at = report_started_at or time.monotonic()
                    last_stage = state.get("stage") or last_stage
                    if time.monotonic() - report_started_at >= timeout_seconds:
                        terminate_process_tree(process.pid)
                        process.wait(timeout=_TERMINATE_WAIT_SECONDS)
                        raise ReportTimeoutError(timeout_seconds, last_stage)
                time.sleep(_POLL_INTERVAL_SECONDS)

        return _load_result(result_path)
    finally:
        if process is not None and process.poll() is None:
            terminate_process_tree(process.pid)
            try:
                process.wait(timeout=_TERMINATE_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                pass
