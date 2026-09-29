---
type: quickstart
title: 快速开始
description: 面向首次接触仓库的读者，说明当前 B/S 版本、启动路径、预处理与质量评估流程、报告超时与直方图限制、部署依赖，以及 base_software 历史基线的定位。
tags: [quickstart, browser-server, point-cloud, quality-assessment, deployment]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T08:08:46.977Z
sources:
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-8fe7ebf00619b8e43f932fa4
    resource: repo://backend/.python-version
  - id: openwiki-source-c578b2dc2526160d08abde24
    resource: repo://backend/app/algos/knn.py
  - id: openwiki-source-4188bfee2e15d969d3152477
    resource: repo://backend/app/config.py
  - id: openwiki-source-af8bc07dd356b94582111a05
    resource: repo://backend/app/core/uploads.py
  - id: openwiki-source-fecf2f8a5b5c8cf503ca5e77
    resource: repo://backend/app/jobs/tools.py
  - id: openwiki-source-115bc96dd839c419e53a5004
    resource: repo://backend/app/report/figures.py
  - id: openwiki-source-181ec9b9e03c27becdc02fe8
    resource: repo://backend/app/report/supervisor.py
  - id: openwiki-source-29449cdcdd8456fbc5b9b089
    resource: repo://backend/app/services/quality.py
  - id: openwiki-source-6b45f4b822f7d3826e57be75
    resource: repo://backend/docs/e2e-checklist.md
  - id: openwiki-source-1771024592351e13dbb973b9
    resource: repo://backend/docs/report-toolchain.md
  - id: openwiki-source-070c6307b3860e1806baf566
    resource: repo://backend/pyproject.toml
  - id: openwiki-source-9025181f12900b1c2ae4adf5
    resource: repo://backend/README.md
  - id: openwiki-source-38cd390b83010a890170c4ab
    resource: repo://base_software/.python-version
  - id: openwiki-source-d69beca5a040440e55fef3c1
    resource: repo://base_software/home_page.py
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
  - id: openwiki-source-5f29572408b9e8962311ba6a
    resource: repo://base_software/README.md
  - id: openwiki-source-f317ee207e1653d2033c81a4
    resource: repo://CONTRIBUTING.md
  - id: openwiki-source-1047363cf615000e4c9bb694
    resource: repo://frontend/package.json
  - id: openwiki-source-56949fc5b7c8934cd12beebd
    resource: repo://frontend/src/api/uploader.ts
  - id: openwiki-source-b3865b441eaafc9ac8594650
    resource: repo://frontend/src/components/DeviationHistogram.vue
  - id: openwiki-source-62c1462ca643d265eb668123
    resource: repo://frontend/src/components/PointCloudViewer.vue
  - id: openwiki-source-77c413f182fc2eead5535edb
    resource: repo://frontend/src/router/index.ts
  - id: openwiki-source-cd5b53dfb8d9f30e726f98f4
    resource: repo://openspec/changes/archive/2026-09-29-document-windows-backend-setup/tasks.md
generated: { by: "codex", at: "2026-09-29T08:08:46.977Z" }
---

# 快速开始

## 这是什么

仓库当前以 B/S 版本为主实现：

- `frontend/`：Vue 3 单页应用；
- `backend/`：FastAPI、同源静态托管、会话/上传/任务/预览/报告 API 与计算进程池；
- `base_software/`：原始 Streamlit 演示和算法行为基线。

浏览器用户通过一个地址访问页面，上传本机文件，提交点云任务，查看进度和预览，并下载结果或 PDF 报告。服务器文件路径不暴露给浏览器。

## 启动 B/S 版本

```bash
# 1) 构建前端
cd frontend
npm ci
npm run build

# 2) 启动后端（同源托管 frontend/dist）
cd ../backend
uv sync --frozen
PORT=8000 scripts/start.sh
```

浏览器访问：

```text
http://<服务器IP>:8000/
```

API 文档位于 `/docs`，部署依赖自检为：

```bash
curl http://<服务器IP>:8000/api/health
```

`start.sh` 会把 `~/.local/bin` 加入 PATH，检查前端 dist，执行 `uv sync --frozen`，然后用 uvicorn 启动服务。Dockerfile 尚未实现，当前路径是 Linux 裸机 + uv。

### Windows 快速路径

Windows 10/11 用户请参考 [B/S 运行、依赖与部署](operations/runtime-and-deployment.md) 和 `backend/README.md` 的“Windows 平台配置”章节。核心差异是：

- 使用 PowerShell 直接执行 `uv sync --frozen` 和 `uv run uvicorn app.main:app --host 0.0.0.0 --port $env:PORT`；
- `backend/scripts/start.sh` 是 Bash 脚本，PowerShell 不能直接运行，需使用 Git Bash/WSL 或跳过该脚本；
- 构建前端需要 Node.js 22.18+ 或 >=24.12.0；
- Windows 报告链路需要另外配置 TeX Live/MiKTeX、Chrome、PyVista 离屏渲染和字体，当前 `/api/health` 对 Chrome 的识别在 Windows 上可能有限制；
- 本次 Windows 文档只完成静态审查和源码对照，尚未在 Windows/PowerShell 实机环境走查。

## 运行前依赖

B/S 运行需要：

- Python 3.10.18（由 uv 按 `.python-version` 管理）。
- Node.js 22.18+ 或 >=24.12.0（与 `frontend/package.json` engines 一致），以及对应 npm，用于构建前端。
- TeX Live/TinyTeX（`latexmk`、`xelatex`、ctex、Fandol），用于 PDF 报告。
- Chrome/Chromium，用于 Kaleido 导出报告图片。
- PyVista 离屏渲染环境（DISPLAY、EGL/OSMesa 或 xvfb）。
- 中文字体与 TeX 宏包。

报告链路和 TinyTeX 安装步骤见 [质量报告生成与工具链](reporting/quality-report-generation.md) 和 `backend/docs/report-toolchain.md`。

## 推荐业务路径

### 1. 先准备 BIM/离散点云

打开 `/preprocess/discretize`，选择或上传网格文件，设置点云间距，提交“网格离散”。结果是当前会话中的 pointcloud artifact，可以直接预览、下载，或作为后续步骤输入。

如果单位不一致，进入 `/preprocess/scale` 做 m/dm/cm/mm 线性换算；需要轻量化时进入 `/preprocess/downsample` 做体素或均匀下采样。

### 2. 对齐扫描点云和 BIM 点云

进入 `/preprocess/registration`：

- “粗配准”调用 FPFH/RANSAC，输出 `_FPFH.xyz`；
- 成功后前端会把粗配准结果自动选入精配准；
- “精配准”依次执行三次 ICP，默认阈值为 `0.05`、`0.03`、`0.005`，输出 `_ICP.xyz`。

配准是否可接受仍需人工检查叠加预览。算法不会自动判断收敛质量。

### 3. 计算尺寸质量

进入 `/quality/assess`：

1. 勾选四个前置确认：已有离散点云、已下采样或忽略、单位一致、已完成匹配。
2. 选择扫描点云和 BIM 点云。
3. 设置单位、偏差方法（Point2Point/Point2Plane）、平面邻域大小和剔除比例。
4. 提交任务，查看阶段进度、四项统计指标、受限浏览器直方图、偏差云预览和 PDF 报告；报告阶段默认 300 秒超时。

`distance` 虽然主要服务 Point2Plane 邻域，但也会以 `distance × 10` 参与环境点筛选，因此切换到 Point2Point 后仍会改变检测点集合。

## 文件与产物

B/S 版本没有浏览器可见的服务器文件对话框：

- 上传通过浏览器文件控件完成，支持 8 MiB 默认分片、SHA-256 校验、断点续传和 24 小时未完成上传保留。
- 每个浏览器会话拥有 `data/sessions/<uuid>/` 工作区，上传、任务和产物按会话隔离。
- 输入与输出通过 artifact id 在页面间复用；下载时恢复原显示文件名。
- 报告 PDF 在任务成功时登记为 report artifact；浏览器展示使用受限 `ui_figure`，原始报告图仍用于 PDF。

如果 HTTP 局域网浏览器没有 Web Crypto，前端会为分片校验回退到纯 JS SHA-256。部分虚拟机或 GPU 黑名单环境无法创建 WebGL2 时，三维预览会显示明确错误，但下载和后续计算仍可使用。

## 已知限制

- 无登录、无权限系统，按内网演示使用。
- 点云预览依赖浏览器 WebGL2；无 WebGL2 时不能显示三维效果。
- Point2Plane 已对近共线/退化平面做 0 值回退，并使用拟合质心投影，不再因法向量 z 分量为 0 产生 NaN/Inf。
- 报告生成默认 300 秒超时（可用 `WUYE_REPORT_TIMEOUT_SECONDS` 调整）；超时任务失败、不登记 PDF，并在错误中报告最后阶段。
- 浏览器直方图最多 256 个柱和 20 个刻度；Plotly 接收前会复制为普通 JSON，避免 Vue 响应式代理卡住 renderer。
- 服务重启不会恢复运行中任务，遗留任务会标记为 interrupted。
- 只支持单 Web 实例的进程内会话锁；没有 Redis/SQLite/分布式锁。
- Docker、HTTPS、反向代理和外部认证未实现。

## 历史 base_software

`base_software/` 仍是 Streamlit 单体演示，入口为 `home_page.py`，`pages/` 提供点云预处理和尺寸质量评估页面。它使用本机 Tk 文件对话框、应用根目录下的 `cache/` 文本路径和 `os.startfile` 输出目录操作，适合作为本地桌面演示或数值基线，不是当前 B/S 部署方式。原始 README 还记录了局域网只能访问部署机本地文件等历史问题。

## 继续阅读

- [仓库与应用架构总览](architecture/application-overview.md)
- [浏览器—服务端架构](architecture/browser-server-architecture.md)
- [点云预处理 B/S 工作流](workflows/point-cloud-preprocessing.md)
- [尺寸质量评估 B/S 工作流](workflows/dimension-quality-assessment.md)
- [B/S 运行、依赖与部署](operations/runtime-and-deployment.md)
- [测试、Golden 基线与端到端验收](development/testing-and-golden-parity.md)

## OpenWiki 维护

本仓库是私有仓库，没有配置 GitHub Actions，也不依赖定时工作流维护 OpenWiki。初始化或更新只由维护者在本地显式执行；不要创建或恢复 `openwiki-update.yml`，也不要为该流程配置 Actions secrets。
