"""会话目录清理：安全路径校验、独立进程删除与并发保护。"""

from __future__ import annotations

import multiprocessing
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.sessions import SessionStore, is_valid_session_id


class SessionCleanupError(RuntimeError):
    """清空目标非法或清理流程无法启动。"""


class SessionCleanupBusy(SessionCleanupError):
    """同一会话已有清理流程。"""


@dataclass(frozen=True)
class CleanupResult:
    ok: bool
    message: str | None = None


def _validate_target(target: Path, root: Path) -> Path:
    """解析并校验目标目录，拒绝越界、符号链接和非会话目录。"""
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise SessionCleanupError(f"会话根目录不可访问: {root}") from exc
    if not resolved_root.is_dir():
        raise SessionCleanupError(f"会话根目录不是目录: {resolved_root}")
    if not is_valid_session_id(target.name):
        raise SessionCleanupError(f"非法会话目录: {target}")
    if target.is_symlink():
        raise SessionCleanupError(f"拒绝删除符号链接: {target}")
    try:
        resolved_target = target.resolve(strict=True)
    except OSError as exc:
        raise SessionCleanupError(f"会话目录不存在或不可访问: {target}") from exc
    if resolved_target.parent != resolved_root:
        raise SessionCleanupError(f"会话目录越界: {resolved_target}")
    if not resolved_target.is_dir():
        raise SessionCleanupError(f"会话目标不是目录: {resolved_target}")
    return resolved_target


def resolve_session_dir(store: SessionStore, session_id: str) -> Path:
    """把当前请求的 session id 解析为安全的会话目录。"""
    try:
        target = store.session_dir(session_id)
    except (TypeError, ValueError) as exc:
        raise SessionCleanupError(f"非法会话 id: {session_id!r}") from None
    return _validate_target(target, store.root)


def _delete_session_dir(target_raw: str, root_raw: str, result_conn: Any) -> None:
    """子进程入口：删除前再次校验路径，并把结果写回父进程。"""
    try:
        target = _validate_target(Path(target_raw), Path(root_raw))
        shutil.rmtree(target)
    except BaseException as exc:  # noqa: BLE001 - 必须把子进程失败显式带回父进程
        try:
            result_conn.send({"ok": False, "message": f"{type(exc).__name__}: {exc}"})
        except BaseException:  # noqa: BLE001 - 结果通道不可用时由父进程识别为缺少结果
            pass
    else:
        try:
            result_conn.send({"ok": True, "message": None})
        except BaseException:  # noqa: BLE001 - 删除已成功但结果传递失败，父进程不得猜测成功
            pass
    finally:
        try:
            result_conn.close()
        except BaseException:  # noqa: BLE001
            pass


@dataclass
class CleanupOperation:
    """一次清空进程及其一次性结果。"""

    session_id: str
    process: Any
    result_conn: Any
    _result: CleanupResult | None = field(default=None, init=False, repr=False)
    _result_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def wait(self) -> CleanupResult:
        """等待子进程结束并返回结果；多个等待者共享同一次结果。"""
        with self._result_lock:
            if self._result is None:
                self._result = self._wait_once()
            return self._result

    def _wait_once(self) -> CleanupResult:
        try:
            self.process.join()
        except BaseException as exc:  # noqa: BLE001 - 等待失败也必须返回显式结果
            self._close()
            return CleanupResult(False, f"等待清理进程失败: {type(exc).__name__}: {exc}")

        exit_code = getattr(self.process, "exitcode", None)
        try:
            if not self.result_conn.poll(0):
                message = "清理进程未返回结果"
                if exit_code is not None:
                    message += f"（退出码 {exit_code}）"
                return CleanupResult(False, message)
            payload = self.result_conn.recv()
        except BaseException as exc:  # noqa: BLE001 - 读取失败不能误报成功
            return CleanupResult(False, f"读取清理结果失败: {type(exc).__name__}: {exc}")
        finally:
            self._close()

        if not isinstance(payload, dict) or "ok" not in payload:
            return CleanupResult(False, "清理进程返回了非法结果")
        if payload.get("ok") is not True:
            return CleanupResult(False, str(payload.get("message") or "清理失败"))
        if exit_code != 0:
            return CleanupResult(False, f"清理进程退出码异常: {exit_code}")
        return CleanupResult(True, None)

    def _close(self) -> None:
        try:
            self.result_conn.close()
        except BaseException:  # noqa: BLE001
            pass


def start_cleanup_process(store: SessionStore, session_id: str) -> CleanupOperation:
    """校验目标并启动独立的 spawn 删除进程。"""
    target = resolve_session_dir(store, session_id)
    context = multiprocessing.get_context("spawn")
    result_conn, send_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=_delete_session_dir,
        args=(str(target), str(store.root), send_conn),
        name=f"session-cleanup-{session_id}",
    )
    try:
        process.start()
    except BaseException:  # noqa: BLE001 - 启动失败由调用者映射为显式错误
        result_conn.close()
        send_conn.close()
        raise
    send_conn.close()
    return CleanupOperation(session_id=session_id, process=process, result_conn=result_conn)


class SessionCleanupManager:
    """单 Web 实例内按 session 阻止重复清空。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict[str, CleanupOperation | None] = {}

    def start(self, store: SessionStore, session_id: str) -> CleanupOperation:
        with self._lock:
            if session_id in self._active:
                raise SessionCleanupBusy(f"会话正在清空: {session_id}")
            self._active[session_id] = None

        try:
            operation = start_cleanup_process(store, session_id)
        except BaseException:
            self.finish(session_id)
            raise

        with self._lock:
            self._active[session_id] = operation
        threading.Thread(
            target=self._reap,
            args=(operation,),
            name=f"session-cleanup-reaper-{session_id}",
            daemon=True,
        ).start()
        return operation

    def finish(self, session_id: str) -> None:
        with self._lock:
            self._active.pop(session_id, None)

    def is_active(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._active

    def shutdown(self) -> None:
        """等待已启动的删除进程结束，避免应用退出时遗留活跃保护。"""
        with self._lock:
            operations = [operation for operation in self._active.values() if operation is not None]
        for operation in operations:
            operation.wait()
            self.finish(operation.session_id)

    def _reap(self, operation: CleanupOperation) -> None:
        try:
            operation.wait()
        finally:
            self.finish(operation.session_id)
