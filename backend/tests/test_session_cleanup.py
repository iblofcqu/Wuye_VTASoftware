"""会话目录清理：路径安全、子进程结果和重复清空保护。"""

import multiprocessing
import os
import threading
import time
import uuid
from pathlib import Path

import pytest

from app.core.session_cleanup import (
    CleanupOperation,
    CleanupResult,
    SessionCleanupBusy,
    SessionCleanupError,
    SessionCleanupManager,
    _delete_session_dir,
    _validate_target,
    resolve_session_dir,
)
from app.core.sessions import SessionStore


def _write_session_marker(store: SessionStore, session_id: str) -> Path:
    marker = store.session_dir(session_id) / "artifacts" / "sample.bin"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("data", encoding="utf-8")
    return marker


def test_spawned_cleanup_removes_only_current_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    current = store.create()
    other = store.create()
    current_marker = _write_session_marker(store, current.session_id)
    other_marker = _write_session_marker(store, other.session_id)

    manager = SessionCleanupManager()
    operation = manager.start(store, current.session_id)

    assert operation.process.pid != os.getpid()
    result = operation.wait()
    manager.finish(current.session_id)

    assert result.ok is True, result.message
    assert not current_marker.exists()
    assert not store.session_dir(current.session_id).exists()
    assert other_marker.exists()
    assert store.load(other.session_id) is not None


def test_safe_target_rejects_invalid_uuid_symlink_and_outside_path(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    store = SessionStore(root)
    with pytest.raises(SessionCleanupError):
        resolve_session_dir(store, "../../etc/passwd")

    outside = tmp_path / "outside"
    outside.mkdir()
    keep = outside / "keep.txt"
    keep.write_text("keep", encoding="utf-8")
    linked_id = str(uuid.uuid4())
    (root / linked_id).symlink_to(outside, target_is_directory=True)

    with pytest.raises(SessionCleanupError):
        resolve_session_dir(store, linked_id)
    with pytest.raises(SessionCleanupError):
        _validate_target(root.parent / "outside", root)
    assert keep.exists()


def test_child_reports_rmtree_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    record = store.create()
    target = store.session_dir(record.session_id)
    receiver, sender = multiprocessing.Pipe(duplex=False)

    def fail_rmtree(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr("app.core.session_cleanup.shutil.rmtree", fail_rmtree)
    try:
        _delete_session_dir(str(target), str(store.root), sender)
        payload = receiver.recv()
    finally:
        receiver.close()

    assert payload["ok"] is False
    assert "permission denied" in payload["message"]
    assert target.exists()


class _FakeProcess:
    def __init__(self, exitcode: int = 0):
        self.exitcode = exitcode

    def join(self) -> None:
        return None


class _FakeConnection:
    def __init__(
        self,
        *,
        has_result: bool = False,
        payload=None,
        poll_error: BaseException | None = None,
        recv_error: BaseException | None = None,
    ):
        self.has_result = has_result
        self.payload = payload
        self.poll_error = poll_error
        self.recv_error = recv_error
        self.closed = False

    def poll(self, timeout: float) -> bool:
        if self.poll_error is not None:
            raise self.poll_error
        return self.has_result

    def recv(self):
        if self.recv_error is not None:
            raise self.recv_error
        return self.payload

    def close(self) -> None:
        self.closed = True


def _operation(process: _FakeProcess, connection: _FakeConnection) -> CleanupOperation:
    return CleanupOperation(session_id="s1", process=process, result_conn=connection)


def test_operation_reports_missing_result_and_nonzero_exit() -> None:
    missing = _operation(_FakeProcess(exitcode=0), _FakeConnection(has_result=False)).wait()
    assert missing == CleanupResult(False, "清理进程未返回结果（退出码 0）")

    failed_exit = _operation(_FakeProcess(exitcode=2), _FakeConnection(has_result=False)).wait()
    assert failed_exit.ok is False
    assert "退出码 2" in (failed_exit.message or "")


def test_operation_reports_read_error_and_invalid_payload() -> None:
    read_error = _operation(
        _FakeProcess(),
        _FakeConnection(has_result=False, poll_error=RuntimeError("pipe closed")),
    ).wait()
    assert read_error.ok is False
    assert "pipe closed" in (read_error.message or "")

    invalid = _operation(_FakeProcess(), _FakeConnection(has_result=True, payload=["bad"])).wait()
    assert invalid == CleanupResult(False, "清理进程返回了非法结果")

    explicit_failure = _operation(
        _FakeProcess(),
        _FakeConnection(has_result=True, payload={"ok": False, "message": "denied"}),
    ).wait()
    assert explicit_failure == CleanupResult(False, "denied")


class _BlockingOperation:
    def __init__(self, session_id: str, release: threading.Event):
        self.session_id = session_id
        self.release = release

    def wait(self) -> CleanupResult:
        self.release.wait(timeout=5)
        return CleanupResult(True, None)


def test_manager_rejects_duplicate_then_releases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    record = store.create()
    release = threading.Event()
    operation = _BlockingOperation(record.session_id, release)
    monkeypatch.setattr(
        "app.core.session_cleanup.start_cleanup_process",
        lambda store, session_id: operation,
    )
    manager = SessionCleanupManager()

    first = manager.start(store, record.session_id)
    with pytest.raises(SessionCleanupBusy):
        manager.start(store, record.session_id)

    release.set()
    assert first.wait().ok is True
    deadline = time.time() + 2
    while manager.is_active(record.session_id) and time.time() < deadline:
        time.sleep(0.01)
    assert not manager.is_active(record.session_id)

    second = manager.start(store, record.session_id)
    release.set()
    assert second.wait().ok is True
    manager.finish(record.session_id)


def test_manager_releases_guard_when_process_start_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = SessionStore(tmp_path / "sessions")
    record = store.create()

    def fail_start(*args, **kwargs):
        raise RuntimeError("spawn failed")

    monkeypatch.setattr("app.core.session_cleanup.start_cleanup_process", fail_start)
    manager = SessionCleanupManager()

    with pytest.raises(RuntimeError, match="spawn failed"):
        manager.start(store, record.session_id)
    assert not manager.is_active(record.session_id)
