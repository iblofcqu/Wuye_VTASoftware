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

## B/S 版本使用（当前）

前后端分离版本位于 `frontend/`（Vue 3）与 `backend/`（FastAPI），浏览器通过页面按钮或直接访问均可使用；
`base_software/` 的原 Streamlit 演示保留为行为基线。

```bash
# 1) 构建前端（首次或前端变更后）
cd frontend && npm ci && npm run build

# 2) 启动后端（同源托管 frontend/dist，默认端口 8000）
PORT=8000 backend/scripts/start.sh
```

浏览器访问 `http://<服务器IP>:8000/`；依赖自检：`curl http://<服务器IP>:8000/api/health`。

- 服务器依赖安装清单与配置项：见 [`backend/README.md`](backend/README.md)
- 报告链路（TeX/Chromium/离屏渲染/中文字体）细节：见 [`backend/docs/report-toolchain.md`](backend/docs/report-toolchain.md)
- 变更计划与规范：见 `openspec/changes/migrate-demo-to-bs-architecture/`
