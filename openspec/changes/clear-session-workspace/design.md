# Design

## Context

现有会话由 `SessionStore` 以 `data/sessions/<uuid>/` 为唯一真源，目录内包含 `session.json`、`artifacts/`、`uploads/`、`previews/` 和 `work/`。`install_session_support()` 负责在 cookie 失效或会话记录不存在时创建新会话。当前没有会话级删除 API，也没有任何 SSE 实现；任务进度仍由前端轮询 `GET /api/jobs/{job_id}`。

本次变更的关键约束是：删除可能包含大量文件，不能占用 Web 请求线程；删除只能作用于当前请求绑定的会话；删除是破坏性操作，必须让前端明确知道何时成功、何时失败。动机见 `proposal.md`，行为要求见本 change 下的两份 delta spec。

## Goals / Non-Goals

**Goals:**

- 提供可确认、可观察、可重复测试的当前会话清空流程。
- 让目录删除由独立 `spawn` 子进程完成，保持 Web API 对查询、上传和任务请求的响应性。
- 通过 SSE 传输开始、成功和失败结果，成功后让 workspace 恢复为空会话。
- 通过路径校验、冲突检查、并发保护和显式错误避免清空错误目录或误报成功。

**Non-Goals:**

- 不实现任务取消、上传中断或“等待运行中任务结束后再清空”的排队语义。
- 不实现回收站、快照恢复或删除后的事务回滚；删除成功即不可恢复。
- 不把现有任务进度轮询改成 SSE，也不改变现有任务 API。
- 不支持多个 Web 实例共享同一 `data/sessions/` 根目录时的分布式清理协调。

## Decisions

### D1: 删除整个当前会话目录，依赖现有中间件建立新会话

清空目标是 `store.session_dir(request.state.session_id)`，成功时删除整个 `<session_id>/` 目录。这样不需要逐个判断 `artifacts/`、`uploads/`、`previews/`、`work/` 的生命周期，也能保证 `session.json` 不再引用残留文件。删除成功后，下一次请求会走现有中间件：旧会话记录不存在，于是创建新的空会话并更新 cookie。

备选方案是只删除会话目录内容并保留 `session.json`，再把清单重置为空。该方案会引入“目录已删除但清单尚未重置”的中间状态，且删除范围更容易遗漏，因此不采用。

### D2: 使用 `POST /api/session/clear` 承载 SSE 流

新增 `POST /api/session/clear`，响应类型为 `text/event-stream`。选择流式 POST 而不是 `EventSource`，原因是清空具有副作用，`EventSource` 只能发起 GET，浏览器在断线重连时可能重复触发删除。前端使用 `fetch()` 读取流，并手动解析 SSE frame；协议同时保留标准 `event:` 和 `data:` 字段。

事件契约如下，所有 `data` 都是 JSON：

```text
event: started
data: {"state":"started"}

event: success
data: {"state":"success"}

event: error
data: {"state":"error","message":"具体失败原因"}
```

- 成功响应状态为 `200`，先发送 `started`，删除完成后发送 `success` 并关闭流。
- 目录删除失败时仍为已开始的 `200` 流，发送 `error` 后关闭，不能发送 `success`。
- 删除前的请求冲突（活跃任务/上传或重复清空）使用 HTTP `409` 和 JSON `detail`，不启动流。
- 进程启动失败使用 HTTP `5xx` 和 JSON `detail`。
- 响应设置 `Cache-Control: no-cache`、`Connection: keep-alive` 和 `X-Accel-Buffering: no`，避免代理缓存或缓冲流。

备选方案是“先 `POST` 创建 operation id，再由 `EventSource` 订阅状态”。该方案能自然重连，但需要保存 operation 状态、处理订阅者断线和过期清理；本次清空是一次性动作，复杂度不值得。

### D3: 每个清空请求创建独立的 `spawn` 子进程

新增 `backend/app/core/session_cleanup.py`。父进程只做校验、启动子进程和读取结果；实际 `shutil.rmtree()` 在 `multiprocessing.get_context("spawn").Process` 中执行。子进程只接收合法的目标目录字符串，不接收 `SessionStore`、请求对象或其他不可安全跨进程传递的对象。

子进程通过单向 `multiprocessing.Pipe` 返回一个 JSON 可序列化结果；父进程在异步生成器中用 `asyncio.to_thread()` 等非阻塞等待方式读取，避免事件循环被 `join()` 或 `recv()` 阻塞。正常结果是 `{"ok": true}`，异常结果是 `{"ok": false, "message": "<ExceptionType>: <message>"}`。

备选方案包括 `threading.Thread`（不能保证文件系统删除不占用 Web 进程资源）、复用 `JobRunner` 的 `ProcessPoolExecutor`（会与业务任务争抢工作槽位，且任务池生命周期不等同于清空生命周期）和临时拼接 shell 命令（引入命令注入和跨平台风险），均不采用。

### D4: 删除前检查活跃工作，并对同一会话加清空锁

在 `/api/session/clear` 中读取当前 `SessionRecord`，只要存在以下任一情况就返回 `409`，不启动删除进程：

- `jobs` 中存在 `queued` 或 `running` 状态；
- `uploads` 中存在 `uploading` 或 `completing` 状态；
- `SessionCleanupManager` 已记录同一 `session_id` 的清空操作。

清空管理器放在 `app.state.session_cleanup`，使用进程内锁保护按 session 的活跃操作集合。它只用于单 Web 进程内的重复请求保护；多实例部署需要额外的分布式锁，明确不在本次范围内。删除失败或子进程异常退出时释放保护，页面可重新尝试。

本次不强制终止运行中的任务或上传，因为现有系统没有取消协议；直接删除会让 worker 在路径消失后产生不可解释错误，也会让上传状态永久不一致。

### D5: 前端把 SSE 解析和 UI 状态分开

新增 `frontend/src/api/session.ts`：

- `clearSession()` 使用 `fetch('/api/session/clear', { method: 'POST', headers: { Accept: 'text/event-stream' } })`；
- 检查非 2xx HTTP 响应并抛出包含 `detail` 的错误；
- 从 `response.body` 按空行切分 frame，使用 `TextDecoder` 处理 chunk 边界；
- `success` 事件让 Promise 成功，`error` 事件让 Promise 失败，流在成功/失败事件后结束；
- 丢弃空行、注释行和未知事件，遇到缺少 body 或非 `text/event-stream` 的响应时显式失败。

`frontend/src/App.vue` 负责导航布局和用户交互：按钮固定在左侧导航底部；点击后使用 `ElMessageBox.confirm()` 二次确认；请求期间设置 `clearing` 并禁用按钮；成功后设置 workspace 快照为空、调用 `workspace.refresh()`，再显示 `ElMessage.success('删除成功')`；冲突、SSE `error` 和网络错误显示 `ElMessage.error(detail)`。不把 Element Plus 提示逻辑放进 API 模块，也不把服务器路径写入页面。

### D6: 路径安全必须在父进程和子进程两侧校验

父进程只接受 `SessionStore.session_dir()` 生成的路径，并使用 `Path.resolve()` 确认其父目录恰好是 `store.root.resolve()`；目标必须是独立会话目录且不能是符号链接。子进程再次检查目标位于允许的会话根目录下，再调用 `shutil.rmtree()`。非法 session id、越界路径和目录被替换为文件/链接的情况都返回显式错误，不调用删除。

## Affected Files / Modules

- `backend/app/core/session_cleanup.py`（新增）：清空结果、`spawn` 子进程启动、结果管道和会话清理管理器。
- `backend/app/api/session.py`：新增 `POST /api/session/clear`，生成 SSE `StreamingResponse`，执行活跃状态检查和错误映射。
- `backend/app/main.py`：创建清空管理器并挂到 `app.state`，在 lifespan 收尾时释放管理器资源。
- `backend/app/core/sessions.py` 或清空管理器依赖的会话读取边界：复用现有 `session_dir()` 和 `SessionRecord` 数据，不改变 `session.json` 格式。
- `frontend/src/api/session.ts`（新增）：SSE 请求与 frame 解析器。
- `frontend/src/App.vue`：底部按钮、确认弹窗、加载态、成功/失败提示和 workspace 刷新。
- `backend/tests/test_session_clear.py`（新增）：删除成功、失败、路径安全、活跃任务/上传冲突和重复清空。
- `frontend/src/api/__tests__/session.spec.ts`（新增）：分块 SSE、成功/失败事件、HTTP 错误和非法响应测试。

## Risks / Trade-offs

- 删除不可恢复且可能误伤用户数据 → 前端二次确认，后端只使用当前 cookie 对应的 session id，路径校验失败即拒绝；发布前备份 `data/sessions/`。
- 活跃任务检查与实际删除之间仍有极短的并发窗口 → 先完成检查和会话内记录读取，再启动子进程；对同一会话维护清空锁，按钮执行期间禁用；不在本次引入任务取消。
- 子进程崩溃或父进程断开导致只收到部分事件 → 父进程必须根据 pipe 结果或退出码产生 `error`，不能把连接关闭当作成功；删除失败可能留下部分文件，由页面明确提示，用户可重新清空。
- 删除大量文件时 SSE 连接被代理缓冲或断开 → 设置禁用缓冲响应头；前端将异常关闭视为失败；首版不支持断点续传或 operation 重订阅。
- 进程创建失败或 `spawn` 环境不可用 → 路由显式返回 5xx，不启动伪成功流程；清理管理器在 `finally` 释放 session 锁。
- 多 Web 实例共享数据目录 → 进程内清空锁无法阻止另一实例并发写入；当前系统本身已声明单 Web 实例边界，本次不扩展。

## Migration Plan

1. 先合并后端实现与测试，确认 `/api/session/clear` 在隔离测试目录可正常删除且不会影响其他 session。
2. 再合并前端按钮、SSE 解析和 workspace 刷新；前后端必须在同一次发布中启用，避免 UI 调用不存在路由。
3. 发布前确认 `data/sessions/` 已备份或明确无需保留；发布后使用一个测试会话验证成功路径、冲突路径和失败提示。
4. 回滚时先隐藏/移除前端入口，再移除路由和 `app.state.session_cleanup` 注册；已删除目录无法通过代码回滚恢复。
