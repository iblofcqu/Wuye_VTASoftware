# Tasks

## 1. 后端清理核心

- [x] 1.1 在 `backend/app/core/session_cleanup.py` 实现安全目标解析和 `spawn` 子进程删除流程：只接受当前 `SessionStore` 根目录下的合法 UUID 会话目录，子进程执行 `shutil.rmtree()`，并通过 pipe 返回成功或异常消息；运行 `cd backend && uv run pytest tests/test_session_cleanup.py -q`，覆盖嵌套目录成功删除、路径越界/符号链接拒绝和异常结果传递。
- [x] 1.2 在清理模块中实现按 session 的 `SessionCleanupManager`：提供开始/结束保护、重复清空拒绝和进程结果等待，并确保进程启动失败、删除失败或异常退出时都释放保护；用单元测试断言同一 session 的第二个操作被拒绝，且结束保护后可再次启动。
- [x] 1.3 为子进程缺少结果、非零退出码和父进程读取异常补充显式错误路径，确保不会生成成功状态；运行清理模块测试，断言所有失败分支都返回可读错误消息。
- [x] 1.4 完成后端清理核心并提交为一个细粒度 commit（例如 `feat(session): add isolated workspace cleanup process`）；提交前运行 `git diff --check`、复核 `git status`，确认只包含清理核心和对应测试。

## 2. 会话清空 API 与 SSE

- [x] 2.1 在 `backend/app/api/session.py` 新增 `POST /api/session/clear` 的删除前检查：拒绝 `queued`/`running` 任务、`uploading`/`completing` 上传和同一会话的重复清空，返回包含具体原因的 HTTP `409`；运行 API 测试覆盖每种冲突，断言会话目录未被删除。
- [x] 2.2 在同一路由接入 `StreamingResponse` 和 `text/event-stream` 响应头，按顺序发送 `started`、`success` 或 `error` 事件；运行测试读取流，断言成功事件后关闭、失败时存在 `error.message` 且没有 `success`。
- [x] 2.3 在 `backend/app/main.py` 创建 `SessionCleanupManager` 并挂到 `app.state`，在应用 lifespan 中按现有单 Web 进程模型释放资源；运行应用工厂/会话测试，断言 `create_app()` 装配完成且关闭不会留下活跃清理保护。
- [x] 2.4 运行 `cd backend && uv run pytest -q`，确认新增测试与现有会话、任务、上传测试全部通过；完成后端 API 变更并提交为一个细粒度 commit（例如 `feat(session): stream workspace clear over sse`），提交前复核暂存内容。验证记录：相关测试 `28 passed`；完整后端测试 `145 passed, 1 failed`，失败为既有 `test_point2plane_error_parity`，本次未触碰 `knn.py` 或该基线测试。

## 3. 前端 SSE 客户端

- [x] 3.1 新增 `frontend/src/api/session.ts`，实现 `POST /api/session/clear` 的 `fetch` 流读取、`TextDecoder` chunk 缓冲、SSE frame 解析，以及 `started`/`success`/`error` 状态转换；为分块到达的事件、连续多个事件和 `data` JSON 错误编写 Vitest 测试。
- [x] 3.2 为非 2xx JSON 错误、缺少 `response.body`、非 `text/event-stream` 响应和流异常关闭补充显式失败处理；运行 `cd frontend && npm run test:unit -- src/api/__tests__/session.spec.ts` 和 `npm run type-check`，断言不会把流结束误判为成功。
- [x] 3.3 完成后端无关的前端 API 客户端变更并提交为一个细粒度 commit（例如 `feat(frontend): add session clear sse client`）；提交前运行 `git diff --check` 和 `git status`，确认未夹带 UI 外改动。

## 4. 导航栏清空入口

- [x] 4.1 修改 `frontend/src/App.vue`，在左侧导航底部固定“清空会话文件”按钮，使用 `ElMessageBox.confirm()` 二次确认，并在清空期间设置 loading/disabled，防止重复点击。
- [x] 4.2 接入 `clearSession()`：成功后清空 workspace 快照、调用 `workspace.refresh()` 创建新空会话并显示成功提示；冲突、SSE `error`、网络异常和解析异常必须显示具体失败原因且不显示成功提示。
- [x] 4.3 运行 `cd frontend && npm run type-check && npm run test:unit && npm run build-only`，并用本地前端做一次按钮取消确认和成功/失败提示的手动冒烟测试；完成后提交为一个细粒度 commit（例如 `feat(frontend): add workspace clear action to navigation`）。冒烟记录：浏览器确认取消不触发结果；mock SSE 成功显示“删除成功”，失败显示“模拟清空失败”；真实临时后端 SSE 删除另行用终端验证。

## 5. 集成验证

- [x] 5.1 启动后端和前端，在浏览器中上传或生成一个可下载产物，点击清空并确认：观察 SSE 请求、删除成功提示、workspace 列表为空，以及刷新页面后仍为空的新会话；验证 `data/sessions/` 下旧目录已消失且其他会话目录未被修改。验证记录：真实临时后端验证 `started`/`success`，当前目录删除、其他会话及其 artifact 保留；浏览器成功提示通过本地 mock SSE 验证，避免 GUI 删除真实数据。
- [x] 5.2 在存在排队/运行任务或未完成上传时点击清空，验证页面显示明确冲突原因且会话目录和任务/上传状态均保持不变；连续点击按钮时验证只发起一个清空请求。验证记录：真实后端未完成上传返回 `409` 且目录保留；UI mock `409` 显示具体 detail；请求期间按钮 `isEnabled() === false`，请求计数只增加 1。
- [x] 5.3 运行全量后端 `cd backend && uv run pytest -q` 与前端 `cd frontend && npm run test:unit && npm run type-check && npm run build-only`，记录完整结果；若集成修复产生额外改动，补充对应回归测试后再提交。验证记录：后端全量 `145 passed, 1 failed`（既有 `test_point2plane_error_parity`），排除该无关测试 `145 passed, 1 deselected`；前端 `27 passed`，type-check 与 build 通过。
- [x] 5.4 复核 `git status`、`git diff` 和提交历史，确认每个提交只覆盖对应的清理核心、API、SSE 客户端或导航入口，工作区不残留测试数据和无关文件。验证记录：功能提交为 `fbade9c`、`29e788c`、`d9648bd`、`a715516`，每个提交范围符合对应模块；仅剩 OpenSpec change 文档待提交。
