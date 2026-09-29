---
type: workflow-guide
title: 异步任务执行与进度
description: 说明任务提交、工具注册、ProcessPoolExecutor、state.json/progress.json、API 轮询、池容量排队、失败和重启中断的完整生命周期。
tags: [workflow, jobs, process-pool, progress, failure]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-1e4906236443e4dd6f7dc409
    resource: repo://backend/app/api/jobs.py
  - id: openwiki-source-6fc4799efc83678e01873d25
    resource: repo://backend/app/jobs/models.py
  - id: openwiki-source-5cd8a5b32eb393895819dfdc
    resource: repo://backend/app/jobs/runner.py
  - id: openwiki-source-24a943f3d4ce3be6822a4891
    resource: repo://backend/app/jobs/store.py
  - id: openwiki-source-fecf2f8a5b5c8cf503ca5e77
    resource: repo://backend/app/jobs/tools.py
  - id: openwiki-source-eddc463742bcffadfedda8a1
    resource: repo://backend/tests/test_jobs_api.py
  - id: openwiki-source-b90c8ebf4d4e394d1aa824cc
    resource: repo://backend/tests/test_jobs_failure_interrupt.py
  - id: openwiki-source-d5f0261ae78e40f8e9af041b
    resource: repo://backend/tests/test_jobs_runner.py
  - id: openwiki-source-4f924e32c75e1a54e0a66e37
    resource: repo://frontend/src/api/jobs.ts
  - id: openwiki-source-d20ee48184829b39dda5f106
    resource: repo://frontend/src/components/JobProgress.vue
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 异步任务执行与进度

## 任务模型

`JobRecord` 的状态集合为：

```text
queued -> running -> succeeded / failed / interrupted
```

每条任务记录包含 `id`、`tool`、状态、创建/更新时间、参数、错误、结果摘要和内部交接字段。任务记录保存在当前会话的 `session.json` 中，运行中的阶段进度则保存在任务工作目录。

## 提交与输入解析

前端先上传输入文件并拿到 artifact id，再调用：

```text
POST /api/tools/{tool}/jobs
```

请求体包含 `inputs`（artifact id 字典）和 `params`。后端任务 API 会：

1. 检查工具是否存在于 `TOOL_REGISTRY`。
2. 按 `INPUT_SPECS` 检查必填输入键。
3. 从当前会话查找输入 artifact，并把 artifact id 解析为内部文件路径和显示名称。
4. 创建 `JobRecord`，写入 `session.json`。
5. 把 worker 函数、参数、输入路径和工作目录提交给进程池。
6. 立即返回 202 和任务记录。

当前工具包括网格离散、尺寸缩放、两种下采样、FPFH 粗配准、ICP 精配准和质量评估。质量评估只接受当前会话中的 scan/bim artifact，不接受服务器路径。

## 进程池与排队

`JobRunner` 懒加载一个 `ProcessPoolExecutor`：

- 最大 worker 数来自 `WUYE_JOB_POOL_SIZE`，默认 2。
- 使用 `spawn` 上下文，避免子进程继承 Web 进程状态。
- 提交后任务先以 `queued` 写入会话；被 worker 接管后，`state.json` 出现，查询时状态显示为 `running`。
- 超过池容量的任务保持 `queued`，不会阻塞 Web 请求线程。

任务完成回调由提交时的 future callback 触发，负责登记输出产物和更新最终状态。当前没有任务取消 API，也没有跨进程恢复正在执行任务的机制。

## Worker 状态与进度

worker 入口在自己的 `<work_dir>` 中写入：

```json
{"state": "running", "pid": 12345}
```

服务层通过 `progress(stage, done, total)` 回调写入 `progress.json`，例如：

```json
{
  "stage": "第2/4步 环境点云及缺失点云剔除",
  "done": 2,
  "total": 4,
  "updated_at": "..."
}
```

`GET /api/jobs/{job_id}` 会合并：

- `session.json` 中的任务记录；
- 工作目录中的 `state.json`；
- 工作目录中的 `progress.json`。

因此页面的百分比是**阶段进度**，不是算法内部精确进度。网格离散的主要计算没有 Open3D 回调，进度条会在“读取网格并离散 1/2”阶段停留到该计算返回。

## 前端轮询与展示

`JobProgress.vue` 观察 `jobId`：

- 每次 jobId 变化时中止旧轮询，创建新的 `AbortController`。
- `pollJob()` 默认每 1000 ms 请求一次 `GET /api/jobs/{id}`。
- 收到 `succeeded`、`failed` 或 `interrupted` 后返回最终任务并触发 `finished` 事件。
- 组件卸载时中止轮询，避免离开页面后继续请求。

`useToolJob.run()` 提交任务并保存 job id；完成回调会刷新 workspace 会话快照，使新产物出现在结果区。页面显示阶段名、`done/total`、状态标签和失败原因。

## 成功路径

1. worker 返回 `outputs`、`summary` 和可选的 `internal_outputs`。
2. runner 遍历 `outputs`，调用 `register_artifact(..., move=True)` 把工作目录文件移动到 `artifacts/`。
3. 任务写入 `succeeded`、结果 artifact 列表和摘要。
4. 前端刷新会话并启用预览、下载或后续步骤的输入选择。

如果输出文件缺失、类型非法或登记失败，任务会变为 `failed`，并不会产生可用的成功产物。

## 失败与中断

- 工具抛出的异常被 runner 捕获并写成 `failed`，错误文本包含异常类型和消息。
- 参数非法会在 worker 内或提交前失败，页面通过任务错误或 HTTP 4xx 显式展示。
- `result` 只在成功登记后才写入；失败任务不会返回可误用的产物。
- 服务重启时 `interrupt_leftover_jobs()` 扫描所有会话，把遗留 `queued`/`running` 任务改为 `interrupted`，错误为“服务重启导致任务中断”。
- Web 进程不会在重启后重新拾取已中断任务；用户需要重新提交。

任务错误当前只保存 `type: message`，没有持久化完整 traceback；需要栈信息时应查看 worker 进程输出或任务工作目录中的中间文件。

## 并发与一致性的边界

- 会话清单写入受 `SessionStore` 进程内锁保护，但进程池 worker 不直接修改 `session.json`。
- 任务工作目录按 job id 隔离，减少同一会话内任务互相覆盖文件的可能。
- `view_job()` 读取 `progress.json` 失败时会忽略该文件的解析错误，保留会话中的状态，但仍可能缺少阶段进度。
- 当前模型面向单 Web 实例；多实例共享同一 data 目录时需要额外的分布式锁和任务协调，尚未实现。

## 相关页面

- [浏览器—服务端架构](../architecture/browser-server-architecture.md)
- [运行时状态、会话与路径](../architecture/runtime-state-and-paths.md)
- [会话、上传与产物工作流](session-upload-and-artifacts.md)
- [点云预处理 B/S 工作流](point-cloud-preprocessing.md)
- [尺寸质量评估 B/S 工作流](dimension-quality-assessment.md)
