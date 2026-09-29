---
type: operations-guide
title: B/S 运行、依赖与部署
description: 说明 Linux 裸机上的 uv 后端、Node 前端构建、start.sh、环境变量、data 工作区、TeX/Chromium/离屏渲染/中文字体健康检查，以及 base_software 历史部署方式与边界。
tags: [operations, deployment, dependencies, uv, linux, health]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-1b77b8e08e1152639efd10bc
    resource: repo://backend/app/api/health.py
  - id: openwiki-source-4188bfee2e15d969d3152477
    resource: repo://backend/app/config.py
  - id: openwiki-source-1d55634d256e9e48fe3ca741
    resource: repo://backend/app/core/health.py
  - id: openwiki-source-070c6307b3860e1806baf566
    resource: repo://backend/pyproject.toml
  - id: openwiki-source-9025181f12900b1c2ae4adf5
    resource: repo://backend/README.md
  - id: openwiki-source-2b58fe0655afe47c26f657c0
    resource: repo://backend/scripts/start.sh
  - id: openwiki-source-b735a19d109c0dd7887674e9
    resource: repo://base_software/functions/PDF.py
  - id: openwiki-source-e8f328734d1e0b7c471f9f72
    resource: repo://base_software/interface/CMGC.png
  - id: openwiki-source-4780a86cf6be10984cc416ee
    resource: repo://base_software/interface/logo.png
  - id: openwiki-source-6df040d645dca68e3b392a74
    resource: repo://base_software/interface/TJBridge.png
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
  - id: openwiki-source-f62fb78e9932aaca3ecc6806
    resource: repo://base_software/path_utils.py
  - id: openwiki-source-55a8d8d548cd1d23cf569ea3
    resource: repo://base_software/pyproject.toml
  - id: openwiki-source-5f29572408b9e8962311ba6a
    resource: repo://base_software/README.md
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# B/S 运行、依赖与部署

## 当前部署路径

B/S 版本在 Linux 裸机上运行，不依赖 Docker。部署链路是：

```bash
# 1) 构建前端
cd frontend
npm ci
npm run build

# 2) 同步并启动后端
cd ../backend
uv sync --frozen
PORT=8000 scripts/start.sh
```

`start.sh` 会：

- 把 `~/.local/bin` 加入 PATH，以便找到用户级 TinyTeX；
- 检查 `frontend/dist` 是否存在，缺失时给出警告；
- 执行 `uv sync --frozen`；
- 用 `uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` 启动服务。

后端启动后，浏览器访问 `http://<服务器IP>:8000/`，FastAPI 同源托管 `frontend/dist`；API 文档默认位于 `/docs`。如果前端未构建，API 仍可启动，但 SPA 无法使用。

## 运行时版本与依赖

B/S 后端使用 Python 3.10.18，由 uv 按 `.python-version` 管理；`backend/pyproject.toml` 固定 `open3d==0.16.0` 和 `numpy~=1.26.4`。这里的 NumPy 降级是运行约束，不是算法改动：Open3D 0.16 与 NumPy 2.x ABI 不兼容，配准/ICP 路径在 Linux 上可能直接崩溃。

前端构建使用仓库声明的 Node 引擎。构建产物不包含 Python 运行时，生产环境只需要 FastAPI 提供静态文件。

## 环境变量

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `WUYE_DATA_DIR` | `<repo>/data` | 会话、上传、产物、预览和任务工作区根目录 |
| `WUYE_SESSION_MAX_AGE_SECONDS` | 30 天 | 会话 cookie 有效期 |
| `WUYE_JOB_POOL_SIZE` | 2 | 计算进程池容量 |
| `WUYE_PREVIEW_MAX_POINTS` | 1,000,000 | 预览轻量化点数上限 |
| `WUYE_MAX_UPLOAD_BYTES` | 5 GiB | 单文件上传大小上限 |
| `WUYE_UPLOAD_CHUNK_SIZE` | 8 MiB | 默认分片大小 |
| `WUYE_UPLOAD_TTL_SECONDS` | 24 小时 | 未完成上传保留时间 |
| `PORT` | 8000 | 启动脚本监听端口 |

`data/` 必须对运行用户可写。服务重启会扫描会话清单，把遗留的 queued/running 任务标记为 interrupted；运行中任务的中间文件和工作目录不会自动恢复执行。

## 报告与浏览器依赖

完整报告链路需要：

- TeX Live 或 TinyTeX，包含 `latexmk`、`xelatex`、`ctex` 和 Fandol 字体；
- Chrome/Chromium，供 Kaleido 导出直方图图片；
- PyVista 离屏截图环境（DISPLAY、EGL/OSMesa 或 xvfb）；
- 中文字体与宏包，确保中文 PDF 可编译。

`backend/docs/report-toolchain.md` 提供了用户级 TinyTeX 安装步骤。当前实现相对 base_software 的报告适配是：

- 使用 `latexmk -xelatex`，不再让 PyLaTeX 默认调用 pdflatex；
- 把基线中的非法单位 `360px` 显式写成 `360pt`；
- 增加圈号字形到中文字体的映射。

## 健康检查

`GET /api/health` 会逐项运行：

| 检查 | 成功条件 |
| --- | --- |
| `tex` | `latexmk` 与 `xelatex` 可在 PATH 找到 |
| `chromium` | 找到 Chrome/Chromium 可执行文件 |
| `offscreen_rendering` | PyVista 能生成非空离屏截图 |
| `chinese_fonts` | `kpsewhich` 能定位 ctex/Fandol 字体文件 |

只有全部通过时状态才是 `ok`；否则返回 `degraded` 和每项具体原因。部署后应先运行：

```bash
curl http://<host>:<port>/api/health
```

## 浏览器访问边界

- Web 版本无登录和权限系统，按内网演示使用；会话隔离通过持久 cookie 实现。
- 浏览器通过同源 `/api` 访问，不需要配置 CORS。
- 上传在 HTTP 局域网环境下仍可用：前端 SHA-256 会优先使用 Web Crypto，`crypto.subtle` 不可用时回退到纯 JS 实现。
- 三维点云预览要求浏览器具备 WebGL2。Chrome 因 GPU 黑名单或虚拟机渲染限制无法创建 WebGL2 时，页面显示明确错误；预览不可用不影响产物下载和后续计算。
- Dockerfile、HTTPS/反向代理、身份认证和跨实例共享存储均未实现，不应把它们描述为当前部署能力。

## 验证命令

```bash
# 后端全量测试（有 TeX 时包括真实 PDF）
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest -q

# 端到端演示清单
PATH="$HOME/.local/bin:$PATH" uv run python tests/e2e_demo_checklist.py

# 前端
cd ../frontend
npm run test:unit
npm run lint
npm run build
```

当前后端 pytest 为 121 passed，前端单测为 6 个文件、18 个用例；报告链路测试在缺少 TeX 时会跳过，不能把跳过当成通过。

## 历史 base_software 部署

`base_software/` 仍是一个单独运行的 Streamlit + uv 项目：

```bash
cd base_software
uv sync --frozen
uv run streamlit run home_page.py
```

它的 `pyproject.toml` 固定 Python 3.10.18，依赖中包括 Streamlit、stpyvista、Open3D、PyVista、PyLaTeX、Kaleido，以及 Windows 条件下的 pywin32；PyInstaller 位于独立的 build dependency group。注意它当前仍固定 `numpy~=2.2.6` 与 `open3d==0.16.0`，这是旧 demo 自身在 Linux 配准路径上的已知风险，B/S 后端已单独固定为 NumPy 1.26。

`base_software/README.md` 记录界面通过 Streamlit 展示并从 `home_page.py` 启动，完整运行需要 TeXstudio 和 Google Chrome；它还记录了原始部署背景：软件可能被解压到服务器上运行，局域网用户的上传/文件选择只指向部署机本地文件，无法看到客户端目录，文档也记录了重新选型或重新开发的讨论。`base_software/interface/` 中的三张品牌图片现已由 git 跟踪，不再是“未跟踪资源”状态。

历史基线的桌面耦合仍然存在：页面使用本机 Tk 文件对话框，多个工作流使用 `os.startfile` 打开输出目录，输入/输出路径保存在应用根目录 `cache/` 下的纯文本文件。因此它适合作为本地桌面/Windows 演示或算法基线，不应直接作为 B/S 部署形态。

## 相关页面

- [快速开始](../quickstart.md)
- [浏览器—服务端架构](../architecture/browser-server-architecture.md)
- [运行时状态、会话与路径](../architecture/runtime-state-and-paths.md)
- [质量报告生成与工具链](../reporting/quality-report-generation.md)
- [开发、提交与质量门禁](../development/quality-workflow.md)
