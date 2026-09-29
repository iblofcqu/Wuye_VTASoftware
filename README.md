# Wuye_VTASoftware

五冶预拼装软件项目：基于点云预拼装的结构构件尺寸质量评定系统（DeviScan-3D）。

## 仓库结构

| 目录 | 说明 |
| --- | --- |
| `base_software/` | 原始 Streamlit 演示程序，作为行为基线保留、不再演进；运行方式见其 README |
| `frontend/` | B/S 前端（Vue 3 + TypeScript + Vite + Element Plus） |
| `backend/` | B/S 后端（FastAPI + 计算进程池，依赖由 uv 管理） |
| `docs/` | 项目文档，含原始 demo 使用说明书 |
| `openspec/` | OpenSpec 变更管理与能力规范 |
| `openwiki/` | 仓库知识库（生成物） |

## 当前状态

B/S 版本正在实施中，变更计划见 `openspec/changes/migrate-demo-to-bs-architecture/`（proposal / specs / design / tasks）。
部署与启动说明将在功能完成后补充到本文件与 `backend/README.md`。
