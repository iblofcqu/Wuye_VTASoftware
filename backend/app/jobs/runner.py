"""任务执行：进程池 + 状态文件 + 完成回调。"""

import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from app import config
from app.core.artifacts import artifact_public_dict, register_artifact
from app.core.sessions import SessionStore, utc_now_iso
from app.jobs import store as job_store
from app.jobs.models import new_job
from app.jobs.tools import TOOL_REGISTRY


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _worker_entry(worker_fn, params: dict, input_paths: dict, input_names: dict, work_dir: str) -> dict:
    """在子进程中执行工具：state.json 标记 running，progress.json 记录阶段进度。"""
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(work_path / "state.json", {"state": "running", "pid": os.getpid()})

    def progress(stage: str, done: int, total: int) -> None:
        _atomic_write_json(
            work_path / "progress.json",
            {"stage": stage, "done": int(done), "total": int(total), "updated_at": utc_now_iso()},
        )

    return worker_fn(params=params, inputs=input_paths, input_names=input_names, work_dir=work_path, progress=progress)


class JobRunner:
    def __init__(self, store: SessionStore, registry: dict | None = None, pool_size: int | None = None):
        self.store = store
        self.registry = dict(registry if registry is not None else TOOL_REGISTRY)
        self.pool_size = int(pool_size or config.JOB_POOL_SIZE)
        self._executor: ProcessPoolExecutor | None = None

    def _get_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self.pool_size, mp_context=multiprocessing.get_context("spawn")
            )
        return self._executor

    def work_dir(self, session_id: str, job_id: str) -> Path:
        return self.store.session_dir(session_id) / config.JOB_WORK_DIR / job_id

    def submit(self, session_id: str, tool: str, params: dict, input_paths: dict, input_names: dict | None = None) -> dict:
        if tool not in self.registry:
            raise ValueError(f"未知工具: {tool}")
        job = new_job(tool)
        job_store.add_job(self.store, session_id, job)
        work_dir = self.work_dir(session_id, job.id)
        work_dir.mkdir(parents=True, exist_ok=True)

        future = self._get_executor().submit(
            _worker_entry,
            self.registry[tool],
            dict(params),
            dict(input_paths),
            dict(input_names or {}),
            str(work_dir),
        )
        future.add_done_callback(lambda done: self._finish(session_id, job.id, done))
        return job_store.get_job(self.store, session_id, job.id)

    def _finish(self, session_id: str, job_id: str, future) -> None:
        work_dir = self.work_dir(session_id, job_id)
        try:
            payload = future.result()
        except BaseException as exc:  # noqa: BLE001 - 失败必须显式返回
            reason = f"{type(exc).__name__}: {exc}"
            job_store.update_job(
                self.store,
                session_id,
                job_id,
                lambda job: job.update({"status": "failed", "error": reason}),
            )
            return

        artifacts = []
        try:
            for output in payload.get("outputs", []):
                artifact = register_artifact(
                    self.store,
                    session_id,
                    output["path"],
                    name=output["display_name"],
                    kind=output["kind"],
                    source_job=job_id,
                    move=True,
                )
                artifacts.append(artifact_public_dict(artifact))
        except Exception as exc:  # noqa: BLE001
            reason = f"产物登记失败: {type(exc).__name__}: {exc}"
            job_store.update_job(
                self.store,
                session_id,
                job_id,
                lambda job: job.update({"status": "failed", "error": reason}),
            )
            return

        result = {"artifacts": artifacts, "summary": payload.get("summary", {})}
        internal = {"internal_outputs": payload.get("internal_outputs", {})}

        def finalize(job) -> None:
            job.update({"status": "succeeded", "error": None, "result": result, "internal": internal})

        job_store.update_job(self.store, session_id, job_id, finalize)

    def view_job(self, session_id: str, job_id: str) -> dict | None:
        record = job_store.get_job(self.store, session_id, job_id)
        if record is None:
            return None
        view = dict(record)
        work_dir = self.work_dir(session_id, job_id)
        if record.get("status") == "queued" and (work_dir / "state.json").exists():
            view["status"] = "running"
        progress_file = work_dir / "progress.json"
        if progress_file.exists():
            try:
                view["progress"] = json.loads(progress_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        view.pop("internal", None)
        return view

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None
