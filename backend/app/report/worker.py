"""在报告子进程中加载并执行 supervisor 传入的目标。"""

import json
import pickle
import sys
from pathlib import Path

from app.report.supervisor import write_progress, write_report_stage


def _write_json(path: Path, payload: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _serialize_result(result):
    if all(hasattr(result, name) for name in ("output_path", "display_name", "summary", "internal_outputs")):
        return {
            "output_path": str(result.output_path),
            "display_name": str(result.display_name),
            "summary": result.summary,
            "internal_outputs": {key: str(value) for key, value in result.internal_outputs.items()},
        }
    return result


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        raise SystemExit("usage: python -m app.report.worker <payload.pkl> <result.json>")

    payload_path = Path(argv[0])
    result_path = Path(argv[1])
    payload = pickle.loads(payload_path.read_bytes())
    work_dir = Path(payload["work_dir"])
    state_path = Path(payload["state_path"])

    def progress(stage: str, done: int, total: int) -> None:
        write_progress(work_dir, stage, done, total)

    def report_progress(stage: str) -> None:
        write_report_stage(state_path, stage)

    try:
        result = payload["target"](
            *payload.get("args", ()),
            progress=progress,
            report_progress=report_progress,
            **payload.get("kwargs", {}),
        )
    except BaseException as exc:  # noqa: BLE001 - 父进程需要把失败写回
        _write_json(
            result_path,
            {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}},
        )
        return 1

    _write_json(result_path, {"ok": True, "result": _serialize_result(result)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
