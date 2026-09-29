"""端到端演示清单：7 个工具 + 报告 + 断点续传 + 失败显式 + 重启中断。

用法（需要 TeX/Chromium/离屏渲染，可先确认 /api/health 为 ok）：
    cd backend && PATH="$HOME/.local/bin:$PATH" uv run python tests/e2e_demo_checklist.py

退出码 0 表示全部场景通过。
"""

import hashlib
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 允许以脚本方式运行

from fastapi.testclient import TestClient  # noqa: E402

from app.config import SESSION_COOKIE_NAME  # noqa: E402
from app.jobs.models import new_job  # noqa: E402
from app.jobs.store import add_job  # noqa: E402
from app.main import create_app  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def wait_job(client: TestClient, job_id: str, timeout: float = 180.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/jobs/{job_id}").json()
        if last["status"] in {"succeeded", "failed", "interrupted"}:
            return last
        time.sleep(0.2)
    raise TimeoutError(f"任务超时: {last}")


def upload(client: TestClient, path: Path, chunk_size: int = 64 * 1024, interrupt: bool = False) -> dict:
    data = path.read_bytes()
    init = client.post(
        "/api/uploads", json={"filename": path.name, "size": len(data), "chunk_size": chunk_size}
    ).json()
    upload_id = init["upload_id"]
    pending = list(init["missing_indices"])
    if interrupt and len(pending) > 1:
        half = pending[: len(pending) // 2]
        pending = pending[len(pending) // 2 :]
        for index in half:
            blob = data[index * chunk_size : (index + 1) * chunk_size]
            response = client.put(
                f"/api/uploads/{upload_id}/chunks/{index}",
                content=blob,
                headers={"X-Chunk-SHA256": hashlib.sha256(blob).hexdigest()},
            )
            assert response.status_code == 200, response.text
        # 模拟"中断后刷新"：查询状态，只补缺失分片
        pending = client.get(f"/api/uploads/{upload_id}").json()["missing_indices"]
    for index in pending:
        blob = data[index * chunk_size : (index + 1) * chunk_size]
        response = client.put(
            f"/api/uploads/{upload_id}/chunks/{index}",
            content=blob,
            headers={"X-Chunk-SHA256": hashlib.sha256(blob).hexdigest()},
        )
        assert response.status_code == 200, response.text
    completed = client.post(f"/api/uploads/{upload_id}/complete").json()
    return completed["artifact"]


def run_tool(client: TestClient, tool: str, inputs: dict, params: dict) -> dict:
    response = client.post(f"/api/tools/{tool}/jobs", json={"inputs": inputs, "params": params})
    assert response.status_code == 202, response.text
    return wait_job(client, response.json()["id"])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="e2e-demo-") as tmpdir:
        root = Path(tmpdir) / "sessions"
        app = create_app(root)

        with TestClient(app) as client:
            client.get("/api/session")
            session_id = client.get("/api/session").json()["session_id"]

            health = client.get("/api/health").json()
            record("依赖自检 /api/health", health["status"] == "ok", health["status"])

            mesh = upload(client, FIXTURES / "sample_mesh.ply", interrupt=True)
            record("断点续传（上传中途查询缺失分片后补齐）", mesh["name"] == "sample_mesh.ply", mesh["name"])

            job = run_tool(client, "mesh-discretize", {"input": mesh["id"]}, {"distance_points": 0.2})
            bim_cloud = job["result"]["artifacts"][0]
            record("① 网格离散", job["status"] == "succeeded", bim_cloud["name"])

            preview = client.get(f"/api/artifacts/{bim_cloud['id']}/preview")
            record("点云预览（WYPV）", preview.status_code == 200 and preview.content[:4] == b"WYPV")

            scan = upload(client, FIXTURES / "sample_scene.xyz")

            job = run_tool(client, "scale", {"input": scan["id"]}, {"origin_unit": "m", "target_unit": "mm"})
            scaled_mm = job["result"]["artifacts"][0]
            record("② 尺寸缩放（m→mm）", job["status"] == "succeeded" and scaled_mm["name"].endswith("_mm.xyz"), scaled_mm["name"])

            job = run_tool(client, "scale", {"input": scaled_mm["id"]}, {"origin_unit": "mm", "target_unit": "m"})
            scaled_back = job["result"]["artifacts"][0]
            record("② 尺寸缩放回 m（单位链路一致）", scaled_back["name"].endswith("_m.xyz"), scaled_back["name"])

            job = run_tool(client, "downsample-voxel", {"input": scaled_back["id"]}, {"voxel_size": 0.1})
            voxel_cloud = job["result"]["artifacts"][0]
            record("③ 体素下采样", job["status"] == "succeeded" and voxel_cloud["name"].endswith("_VD.xyz"), voxel_cloud["name"])

            job = run_tool(client, "downsample-uniform", {"input": scaled_back["id"]}, {"every_k": 2})
            uniform_cloud = job["result"]["artifacts"][0]
            record("③ 均匀下采样", job["status"] == "succeeded" and uniform_cloud["name"].endswith("_UD.xyz"), uniform_cloud["name"])

            job = run_tool(
                client, "register-fpfh", {"moving": voxel_cloud["id"], "fixed": bim_cloud["id"]}, {"voxel_size": 0.2}
            )
            fpfh_cloud = job["result"]["artifacts"][0]
            record("④ FPFH 粗配准", job["status"] == "succeeded" and fpfh_cloud["name"].endswith("_FPFH.xyz"), fpfh_cloud["name"])

            job = run_tool(
                client,
                "register-icp",
                {"moving": fpfh_cloud["id"], "fixed": bim_cloud["id"]},
                {"thresholds": [0.05, 0.03, 0.005]},
            )
            icp_cloud = job["result"]["artifacts"][0]
            record("⑤ ICP 精配准", job["status"] == "succeeded" and icp_cloud["name"].endswith("_ICP.xyz"), icp_cloud["name"])

            job = run_tool(
                client,
                "quality-assess",
                {"scan": icp_cloud["id"], "bim": bim_cloud["id"]},
                {"unit": "m", "method": "Point2Point", "distance": 0.05, "ratio": 0.05},
            )
            report = next((a for a in job["result"]["artifacts"] if a["kind"] == "report"), None)
            summary = job["result"]["summary"]
            record("⑥ 质量评估（指标+直方图）", job["status"] == "succeeded" and summary["check_num"] > 0, f"check_num={summary.get('check_num')}")
            record("⑥ 报告产物命名（取自实际输入的扫描点云名）", bool(report) and "几何质量评估报告" in report["name"] and report["name"].endswith(".pdf"), report["name"] if report else "")

            pdf = client.get(f"/api/artifacts/{report['id']}/download")
            record("⑦ PDF 报告下载", pdf.status_code == 200 and pdf.content[:4] == b"%PDF", f"{len(pdf.content)} bytes")

            preview = client.get(f"/api/jobs/{job['id']}/preview")
            record("⑦ 偏差云预览（mm 标量+seismic）", preview.status_code == 200, f"{len(preview.content)} bytes")

            failure = run_tool(client, "downsample-voxel", {"input": scaled_back["id"]}, {"voxel_size": 0})
            record("失败显式化", failure["status"] == "failed" and "体素尺寸" in (failure["error"] or ""), failure.get("error", ""))

            leftover = new_job("quality-assess", {"ratio": 0.05})
            leftover.status = "running"
            add_job(app.state.session_store, session_id, leftover)

        # 模拟服务重启：同数据目录新建应用，启动时应把遗留任务标记为中断
        restarted = create_app(root)
        with TestClient(restarted) as client:
            client.cookies.set(SESSION_COOKIE_NAME, session_id)
            view = client.get(f"/api/jobs/{leftover.id}").json()
            record("重启中断（遗留任务标记 interrupted）", view["status"] == "interrupted", view.get("error", ""))

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n===== 演示清单结果：{passed}/{len(RESULTS)} 项通过 =====")
    failed = [name for name, ok, _ in RESULTS if not ok]
    if failed:
        print("未通过项:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
