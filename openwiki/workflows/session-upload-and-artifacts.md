---
type: workflow-guide
title: 会话、上传与产物工作流
description: 说明浏览器会话 cookie、分片上传、SHA-256 校验、断点恢复、TTL 清理、产物登记、下载和会话隔离之间的完整数据流。
tags: [workflow, session, upload, artifacts, resume]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-5d593278ee6c8f05c76ca7b5
    resource: repo://backend/app/api/artifacts.py
  - id: openwiki-source-d3cb6830ecaa081440b96d80
    resource: repo://backend/app/api/session.py
  - id: openwiki-source-2ea8d7f25231e75207ba6da8
    resource: repo://backend/app/api/uploads.py
  - id: openwiki-source-4188bfee2e15d969d3152477
    resource: repo://backend/app/config.py
  - id: openwiki-source-8803caea915c45463e82f840
    resource: repo://backend/app/core/artifacts.py
  - id: openwiki-source-641ae98462ef0e5867e3c63c
    resource: repo://backend/app/core/sessions.py
  - id: openwiki-source-af8bc07dd356b94582111a05
    resource: repo://backend/app/core/uploads.py
  - id: openwiki-source-56949fc5b7c8934cd12beebd
    resource: repo://frontend/src/api/uploader.ts
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 会话、上传与产物工作流

## 会话建立

浏览器第一次访问任意请求时，`session` 中间件检查 `wuye_session` cookie：

- cookie 缺失或不是合法 UUID 时创建新会话；
- 把 `session_id` 写入请求状态，后续路由只能访问该会话；
- 会话 ID 变化时下发 `HttpOnly`、`SameSite=Lax`、默认 30 天的 cookie。

会话记录保存在 `data/sessions/<uuid>/session.json`，包含 artifacts、jobs 和 uploads 三类条目。浏览器通过 cookie 获得工作区隔离，不涉及用户登录或身份权限。

## 上传初始化

前端按 `File` 计算文件指纹：

```text
文件名 | 文件大小 | lastModified
```

上传前调用 `POST /api/uploads`，请求包含文件名、大小和可选分片大小。后端会：

- 清洗文件名，只保留最后一个路径组件；
- 根据扩展名推断 `mesh` 或 `pointcloud`；
- 拒绝空大小、超过 `WUYE_MAX_UPLOAD_BYTES`（默认 5 GiB）或非法分片大小；
- 默认分片大小为 8 MiB，允许范围由 `WUYE_UPLOAD_MIN_CHUNK_SIZE` 和 `WUYE_UPLOAD_MAX_CHUNK_SIZE` 控制；
- 创建 `UploadRecord`，计算总片数，并把记录写入 `session.json`。

初始化失败不会创建产物；扩展名不支持的请求直接返回 400，超限返回 413。

## 分片上传协议

每个分片通过：

```text
PUT /api/uploads/{upload_id}/chunks/{index}
X-Chunk-SHA256: <64 位十六进制>
Body: 分片 Blob
```

后端行为：

1. 先检查上传是否属于当前会话。
2. 如果该索引已经在 `received` 中，直接返回当前进度，保持幂等。
3. 根据上传总大小和分片大小计算期望字节数。
4. 读取请求体、累积分片内容并计算 SHA-256。
5. 校验长度和 `X-Chunk-SHA256`，不匹配则拒绝。
6. 先把数据写入 `<index>.part.tmp`，再原子替换为 `<index>.part`。
7. 在会话锁内更新 `received` 和 `chunk_sha256`。

当前实现按分片读取并在内存中收集该分片，再落盘；内存占用上界与单个分片大小相关，不是整文件大小。前端默认并发 2 个分片，因此并发时可能同时在内存中处理两个默认 8 MiB 分片。

## 完成、恢复与校验

`complete` 是幂等操作：

- `status=completed` 且已有 artifact id 时直接返回既有产物。
- 只有所有分片都齐全时才按索引顺序重新组装。
- 组装时再次校验每个分片的长度和 SHA-256，并计算整体 SHA-256。
- 通过后调用 `register_artifact()`，删除上传临时目录，再把上传状态更新为 `completed`。
- 如果某分片校验失败且错误包含索引，会删除该分片、从 `received` 中移除并恢复为 `uploading`，以便只重传该分片。
- 其他组装失败会恢复为可继续上传的状态，或作为请求错误返回。

页面刷新不会保留 `File` 句柄。用户重新选择同一文件时，前端 localStorage 中的指纹会命中已有 upload id，调用状态接口取回 `received_indices` 和 `missing_indices`，只补缺失分片；已接收分片不会重传。服务重启后，只要 `data/sessions/` 和上传临时文件仍在，同一浏览器 cookie 就可以继续查询并补齐上传。

## 前端恢复与重试

`frontend/src/api/uploader.ts` 负责：

- 初始化或恢复上传记录；
- 对缺失分片按 `concurrency` 默认 2 并发上传；
- 每个分片最多重试 3 次，失败按指数退避；
- 分片 SHA-256 优先使用 Web Crypto；
- HTTP 局域网不是安全上下文、`crypto.subtle` 不可用时，回退到 `@noble/hashes` 纯 JS 实现；
- 上传成功后调用 `complete`，再从 pending 列表中移除文件指纹；
- 多文件使用 `Promise.allSettled`，一个文件失败不影响其他文件。

`FileUploader.vue` 使用响应式列表展示每个文件的状态、已完成分片数和错误。上传成功后，`ArtifactPicker` 会刷新 workspace 并把新 artifact 设为当前输入。

## 取消、过期与边界

- 未完成上传可由 `DELETE /api/uploads/{upload_id}` 取消；取消会删除临时分片并把状态标为 `aborted`，重复取消幂等。
- 已完成上传不能取消，正在合并的 `completing` 上传也不能取消。
- `WUYE_UPLOAD_TTL_SECONDS` 默认 24 小时；初始化新上传时会惰性清理超过期限的未完成记录和临时目录。
- 上传大小、分片范围和文件类型非法时均返回显式错误，不登记可用产物。
- 上传记录本身保存在 `session.json`；`GET /api/session` 会移除分片的 SHA-256 映射，避免把内部校验信息返回给浏览器。

## 产物登记与下载

上传完成后，`register_artifact()`：

- 使用 artifact id 生成内部文件名，避免同名覆盖；
- 保存显示名称、类型、大小、生成时间和来源任务；
- 把文件放在当前会话的 `artifacts/` 目录；
- 对外 API 不暴露内部 `path`。

下载接口 `GET /api/artifacts/{artifact_id}/download` 会再次校验 artifact 属于当前会话，并确保解析后的路径仍在会话目录内；然后以原始显示名称返回 `FileResponse`。未知 artifact、跨会话访问、非法路径或缺失文件都显式返回 404/错误响应。

## 相关页面

- [浏览器—服务端架构](../architecture/browser-server-architecture.md)
- [运行时状态、会话与路径](../architecture/runtime-state-and-paths.md)
- [异步任务执行与进度](async-job-execution.md)
- [点云预处理 B/S 工作流](point-cloud-preprocessing.md)
- [快速开始](../quickstart.md)
