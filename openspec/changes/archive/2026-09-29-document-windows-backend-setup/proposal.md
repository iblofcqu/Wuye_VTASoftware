# Proposal

## Why

`backend/README.md` 目前只给出 Linux 依赖安装与启动流程。Windows 用户无法从该文档确认如何准备 Python/uv、前端构建、报告工具链、环境变量和启动命令，容易把 Windows 与 Linux 的路径、安装方式和运行时边界混淆。本次只补充文档，不改变任何后端行为。

## What Changes

- 在 `backend/README.md` 增加 Windows 平台环境配置章节。
- 说明 Windows 下需要的 Python 3.10.18、uv、Node.js/npm、前端构建产物和 PowerShell 启动方式。
- 说明 Windows 报告链路依赖：LaTeX（推荐 MiKTeX 或 TeX Live）、Chrome/Chromium、PyVista 离屏渲染和字体检查。
- 说明 HTTP 局域网访问、会话数据目录、端口/环境变量和 `/api/health` 自检的 Windows 使用方式。
- 明确 Windows 上可能遇到的平台差异与已知限制，例如路径写法、浏览器 WebGL2、报告工具链和 `uv` 命令环境。
- 不修改后端代码、API、依赖锁定或 Linux 部署说明。

## Capabilities

### New Capabilities

无。本次为纯文档变更，没有新增或修改可观察行为。

### Modified Capabilities

无。`skip_specs: true` 已设置在 `openspec/changes/document-windows-backend-setup/.openspec.yaml`；本次不创建 delta specs，也不修改 `openspec/specs/`。

## Impact

- 受影响文件：`backend/README.md`。
- 不影响：`backend/app/`、`frontend/`、测试、API、环境变量默认值、依赖版本、Linux 部署和运行数据格式。
- 文档需要与实际实现保持一致；若 Windows 实测发现实现尚未支持某项能力，应把限制写清楚，而不是把规划写成已实现。

## Rollback Plan

撤销本次变更只需删除 `backend/README.md` 中新增的 Windows 配置章节；没有代码、数据迁移或 API 兼容性回滚工作。

## Coordination

- 由实现者负责在 Windows 环境执行 README 命令并记录实际结果。
- 如果报告工具链（LaTeX/Chrome/离屏渲染）在 Windows 上有额外系统依赖，应与后续部署文档维护保持一致。
- 若需要把 Windows 支持纳入 CI 或自动化测试，另行提出变更；本次只补文档。
