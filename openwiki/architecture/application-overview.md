---
type: architecture-overview
title: 仓库与应用架构总览
description: 说明 monorepo 中 frontend、backend、base_software、docs、openspec 与 openwiki 的职责边界，以及 B/S 实现作为当前主路径、Streamlit 实现作为行为基线的定位。
tags: [architecture, monorepo, browser-server, legacy]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-d3cb6830ecaa081440b96d80
    resource: repo://backend/app/api/session.py
  - id: openwiki-source-5cd8a5b32eb393895819dfdc
    resource: repo://backend/app/jobs/runner.py
  - id: openwiki-source-fecf2f8a5b5c8cf503ca5e77
    resource: repo://backend/app/jobs/tools.py
  - id: openwiki-source-55002f5b1d39cf35fd6d60e2
    resource: repo://backend/app/main.py
  - id: openwiki-source-69b522f10ffdb79d601b4fcf
    resource: repo://frontend/src/main.ts
  - id: openwiki-source-77c413f182fc2eead5535edb
    resource: repo://frontend/src/router/index.ts
  - id: openwiki-source-f84e00765bee83429b57cff5
    resource: repo://frontend/src/stores/workspace.ts
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 仓库与应用架构总览

## 当前主路径

仓库现在同时容纳两套应用形态：

- `frontend/` + `backend/` 是当前 B/S 主实现。浏览器加载 Vue 单页应用，后端 FastAPI 在同一端口托管构建产物并提供业务 API。
- `base_software/` 是原始 Streamlit 单体演示，保留为行为基线和回归参考，不再是当前主交付形态。

迁移没有删除原演示，也没有把原 Streamlit 运行时直接嵌入新服务。B/S 服务从 `backend/app/algos/` 使用算法副本，而 `base_software/functions/` 继续作为数值行为的对照来源。

## 目录职责

| 目录 | 职责 |
| --- | --- |
| `frontend/` | Vue 3 + TypeScript 单页应用、路由、页面、组件、API 客户端与浏览器状态 |
| `backend/` | FastAPI 应用、同源静态托管、会话/产物/上传/任务/预览/报告 API 与计算进程池 |
| `base_software/` | 原始 Streamlit 演示与算法基线；用于对照行为，不是 B/S 服务的运行时依赖 |
| `docs/` | 使用手册与原始 demo 文档 |
| `openspec/` | 已归档变更、主规范与变更配置 |
| `openwiki/` | 由 OpenWiki 维护的仓库知识库 |

## 运行时边界

B/S 版本的基本调用关系是：

```text
浏览器
  -> Vue SPA（frontend/src）
  -> 同源 /api 请求
  -> FastAPI（backend/app/main.py）
  -> 会话/产物/上传/预览存储
  -> JobRunner（进程池）
  -> backend/app/services -> backend/app/algos
```

FastAPI 负责 Web 请求、会话 cookie、静态资源兜底和任务状态查询；真正耗时的点云计算由独立计算进程执行。浏览器端不直接访问服务器文件系统，输入文件通过浏览器上传，结果通过会话产物和下载接口获取。

## 前端职责

`frontend/src/main.ts` 负责创建 Vue、Pinia、Router 和 Element Plus。路由在 `frontend/src/router/index.ts` 中声明首页、点云预处理和尺寸质量评估页面；页面组件通过 `frontend/src/api/` 调用后端 API，通过 `frontend/src/stores/workspace.ts` 保存当前会话快照。

前端不负责算法执行，也不执行业务数据持久化。它负责：

- 文件选择、会话产物选择和上传进度展示。
- 任务提交、任务状态轮询和失败原因展示。
- 点云预览、直方图与 PDF 下载入口。
- 与原始 demo 一致的中文页面结构与导航。

## 后端职责

`backend/app/main.py` 创建 FastAPI 应用，安装会话中间件，挂载 API 路由，并在 `frontend/dist` 存在时托管前端静态资源。后端按职责拆分为：

- `api/`：HTTP 路由和请求参数边界。
- `core/`：会话、产物、上传、预览和部署自检。
- `jobs/`：任务模型、存储、进程池 runner 与工具注册表。
- `services/`：把算法包装成带参数校验和阶段进度的工具服务。
- `algos/`：从 base_software 迁移或适配的数值算法。
- `report/`：报告图片与 PDF 生成。

这种分层让 Web 层不直接编排算法细节，计算进程也不直接修改会话清单；任务完成后由 runner 统一登记产物。

## 历史基线的定位

`base_software/` 仍是原始的 Streamlit 单体：`home_page.py` 提供应用外壳，`pages/` 使用 Streamlit 内置多页面导航，页面通过本机 Tk 对话框选文件并把路径写入 `cache/`。这些行为仍可用于理解“原演示的语义是什么”，但不是当前 B/S 部署路径。

当前 B/S 代码没有导入 `base_software` 的页面或路径缓存协议。它使用 `backend/app/algos/`、`backend/app/services/` 和 `data/sessions/` 工作区；原 demo 的差异通过 golden parity 测试、设计记录和运维文档显式保留。

## 架构约束

- 无登录、仅面向内网演示；浏览器通过同源地址访问。
- 前端构建产物由 FastAPI 同源托管，避免生产环境额外配置 CORS 和静态服务器。
- Web 进程与计算进程分离；计算容量由 `WUYE_JOB_POOL_SIZE` 控制。
- 算法行为以 base_software 为基线；未获批准的算法修复不随架构迁移混入。
- Docker 尚未实现；当前部署路径是 Linux 裸机 + uv，详见运行与部署页面。

## 相关页面

- [浏览器—服务端架构](browser-server-architecture.md)
- [运行时状态、会话与路径](runtime-state-and-paths.md)
- [点云预处理 B/S 工作流](../workflows/point-cloud-preprocessing.md)
- [尺寸质量评估 B/S 工作流](../workflows/dimension-quality-assessment.md)
- [B/S 运行、依赖与部署](../operations/runtime-and-deployment.md)
