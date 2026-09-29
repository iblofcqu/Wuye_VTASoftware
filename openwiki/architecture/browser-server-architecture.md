---
type: architecture-guide
title: 浏览器—服务端架构
description: 说明 Vue 前端、FastAPI 同源服务、会话中间件、业务 API、计算进程池与质量评估报告 supervisor 之间的运行时关系，以及浏览器结果渲染边界。
tags: [architecture, frontend, backend, fastapi, same-origin]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T08:08:46.977Z
sources:
  - id: openwiki-source-1e4906236443e4dd6f7dc409
    resource: repo://backend/app/api/jobs.py
  - id: openwiki-source-d3cb6830ecaa081440b96d80
    resource: repo://backend/app/api/session.py
  - id: openwiki-source-5cd8a5b32eb393895819dfdc
    resource: repo://backend/app/jobs/runner.py
  - id: openwiki-source-fecf2f8a5b5c8cf503ca5e77
    resource: repo://backend/app/jobs/tools.py
  - id: openwiki-source-55002f5b1d39cf35fd6d60e2
    resource: repo://backend/app/main.py
  - id: openwiki-source-115bc96dd839c419e53a5004
    resource: repo://backend/app/report/figures.py
  - id: openwiki-source-181ec9b9e03c27becdc02fe8
    resource: repo://backend/app/report/supervisor.py
  - id: openwiki-source-082db4a97118dbe27f557896
    resource: repo://frontend/src/api/http.ts
  - id: openwiki-source-4a11add55cd5e054f02cd8e1
    resource: repo://frontend/src/api/index.ts
  - id: openwiki-source-4f924e32c75e1a54e0a66e37
    resource: repo://frontend/src/api/jobs.ts
  - id: openwiki-source-b3865b441eaafc9ac8594650
    resource: repo://frontend/src/components/DeviationHistogram.vue
  - id: openwiki-source-c0d31886011163a6c93bffe9
    resource: repo://frontend/src/utils/qa.ts
  - id: openwiki-source-d5099a190ac06d937fadf92d
    resource: repo://frontend/src/views/quality/QualityAssessView.vue
generated: { by: "codex", at: "2026-09-29T08:08:46.977Z" }
---

# 浏览器—服务端架构

## 运行时拓扑

当前 B/S 版本采用同源部署：Vue 构建产物由 FastAPI 直接托管，浏览器只需要访问一个服务地址。生产运行链如下：

```text
浏览器
  -> Vue SPA（frontend/src）
  -> fetch('/api/...')（同源、携带会话 cookie）
  -> FastAPI（backend/app/main.py）
  -> 会话/产物/上传/预览存储
  -> JobRunner 进程池
  -> services -> algos
       └─ quality-assess -> report supervisor -> report worker
```

这种结构让浏览器不需要知道服务器文件路径，也不需要跨域访问。上传、任务提交、状态查询、预览和下载都通过同源 HTTP API 完成。质量评估的报告阶段位于额外的嵌套子进程中，这样 PyVista、Kaleido 或 LaTeX 的阻塞不会占用 Web 进程。

## 前端入口与 API 边界

`frontend/src/main.ts` 创建 Vue 应用并安装 Pinia、Router 和 Element Plus。`frontend/src/api/index.ts` 集中声明后端路径：

- `/api/session`：当前会话快照。
- `/api/uploads`：上传初始化、分片、状态、完成与取消。
- `/api/tools/{tool}/jobs`：提交工具任务。
- `/api/jobs/{job_id}`：查询任务进度与结果。
- `/api/artifacts/{artifact_id}/download`、`/api/artifacts/{artifact_id}/preview`：产物下载与预览。
- `/api/jobs/{job_id}/preview`：质量评估偏差云预览。

`frontend/src/api/http.ts` 统一使用 `credentials: 'same-origin'` 并把非 2xx 响应转换为带状态码的 `ApiError`。任务轮询由 `frontend/src/api/jobs.ts` 完成，默认每秒查询一次，直到 `succeeded`、`failed` 或 `interrupted`。

## FastAPI 应用组成

`backend/app/main.py` 的 `create_app()` 同时做四件事：

1. 创建 `SessionStore` 和 `JobRunner`。
2. 在 lifespan 启动阶段处理遗留任务，在关闭阶段停止 runner。
3. 安装会话中间件并挂载 artifacts、uploads、jobs、preview、health 路由。
4. 如果 `frontend/dist` 存在，挂载 `/assets` 并把其余非 API 路径回退到 SPA 的 `index.html`。

因此后端既是业务 API 服务，也是生产环境的前端静态服务器。若前端未构建，API 仍可启动，但浏览器无法获得完整 SPA。

## 会话中间件

`backend/app/api/session.py` 在每个 HTTP 请求进入路由前检查 `wuye_session` cookie：

- cookie 缺失或不是合法 UUID 时创建新会话；
- 当前会话 ID 写入 `request.state.session_id`，各路由仅访问该会话；
- 会话 ID 变化时通过 `HttpOnly`、`SameSite=Lax` 的 cookie 下发，默认有效期为 30 天；
- `GET /api/session` 返回会话清单，但不返回产物的内部存储路径，也不返回上传分片的 SHA-256 映射。

登录和权限系统不在当前实现范围内；会话隔离依赖浏览器 cookie，而不是用户身份。

## HTTP API 边界

| 边界 | 主要职责 | 关键限制 |
| --- | --- | --- |
| `/api/session` | 查询当前会话、产物、任务和上传清单 | 只返回当前 cookie 对应会话 |
| `/api/uploads/*` | 初始化、分片上传、状态、完成、取消 | 只有完整且校验通过的合并文件才登记为产物 |
| `/api/tools/*/jobs` | 校验输入产物并提交计算任务 | 任务只引用当前会话中的产物 ID |
| `/api/jobs/*` | 查询任务状态、阶段进度与结果 | 运行状态可能来自 `state.json`/`progress.json` |
| `/api/artifacts/*` | 下载产物、生成点云预览 | 路径必须落在当前会话目录内 |
| `/api/health` | 检查部署依赖 | 返回 `ok` 或 `degraded` 及逐项原因 |

未知的 `/api/*` 路径不会进入 SPA 的业务 API，而由静态回退返回 404；业务路由优先于 catch-all。

## Web 进程与计算进程

Web 路由不执行点云算法。提交任务时，`JobRunner.submit()` 先写入任务记录，再把工具函数、参数、输入路径和工作目录提交给 `ProcessPoolExecutor`。进程池使用 `spawn` 上下文，默认容量 2，可由 `WUYE_JOB_POOL_SIZE` 覆盖。

worker 在自己的工作目录中写入 `state.json` 和 `progress.json`；Web 层查询任务时再读取这些文件，把运行状态与阶段进度合并到响应。任务完成回调负责把输出文件登记为会话产物。这样即使计算耗时较长，会话查询和其他页面请求仍由 Web 进程独立处理。

质量评估额外通过 `report supervisor` 启动报告 worker。supervisor 读取 `report_state.json` 的当前阶段，默认在 300 秒后调用进程树清理；超时错误包含秒数和最后阶段，报告产物不会登记。Linux 使用独立进程组与 `SIGKILL`，Windows 使用 `taskkill /F /T`。

## 浏览器结果渲染边界

质量评估结果的 `summary.figure` 保留原始报告图，`summary.ui_figure` 是浏览器展示用图：柱数最多 256、x 轴刻度最多 20。前端优先选择 `ui_figure`，并在调用 `Plotly.react()` 前通过 `toPlainFigure()` 克隆为普通 JSON 对象。

这个克隆是实际运行时契约的一部分：Vue 的深层响应式 Proxy 会让 Plotly 遍历代理图时长时间占用 renderer 主线程，即使直方图只有几十个柱。普通 JSON 把渲染边界限制在受限图形数据内。

## 一条典型请求链

以网格离散为例：

```text
上传网格 -> /api/uploads 分片 -> complete 登记 mesh artifact
提交任务 -> /api/tools/mesh-discretize/jobs
轮询状态 -> /api/jobs/{id}
任务完成 -> runner 登记 pointcloud artifact
页面刷新会话 -> /api/session
显示结果 -> /api/artifacts/{id}/preview + /download
```

这条链路中的状态所有权很清楚：浏览器只保存 UI 选择和任务 ID；会话清单与产物元数据属于 `data/sessions/`；运行中进度属于任务工作目录；算法执行属于独立子进程。任何一步失败都会通过 HTTP 错误或任务失败状态显式返回。

## 相关页面

- [仓库与应用架构总览](application-overview.md)
- [运行时状态、会话与路径](runtime-state-and-paths.md)
- [会话、上传与产物工作流](../workflows/session-upload-and-artifacts.md)
- [异步任务执行与进度](../workflows/async-job-execution.md)
- [尺寸质量评估 B/S 工作流](../workflows/dimension-quality-assessment.md)
- [质量报告生成与工具链](../reporting/quality-report-generation.md)
- [B/S 运行、依赖与部署](../operations/runtime-and-deployment.md)
