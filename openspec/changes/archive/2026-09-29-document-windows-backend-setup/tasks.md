# Tasks

> 验证备注（2026-09-29）：当前工作区没有 Windows/PowerShell 实机环境，经用户确认，放弃 Windows 实机实验性验证。
> 1.1、1.2、3.1 按静态文档审查、命令与源码对照、`git diff --check` 和 `openspec validate` 完成，不声称已实际执行 Windows 命令。

## 1. Backend README Content

- [x] 1.1 在 `backend/README.md` 增加“Windows 平台配置”章节，覆盖 Python 3.10.18、uv 安装/校验、PowerShell 下的 `uv sync --frozen` 和直接使用 `uv run uvicorn` 启动后端；验证：按 README 命令能在 PowerShell 中完成一次后端启动并访问 `/docs`。
- [x] 1.2 在同一章节说明 Windows 下前端构建步骤（Node.js/npm、`npm ci`、`npm run build`）以及 `frontend/dist` 是后端同源静态托管的前置条件；验证：构建后 `frontend/dist/index.html` 存在，后端访问根页面返回 SPA。
- [x] 1.3 说明 `backend/scripts/start.sh` 是 Bash 脚本，Windows PowerShell 不能直接执行；给出 Git Bash/WSL 使用方式或推荐直接用 PowerShell 运行 uvicorn；验证：README 中不把 `.sh` 启动脚本描述为 PowerShell 命令。
- [x] 1.4 在 Windows 章节列出环境变量、`data/` 可写目录、`PORT`、`0.0.0.0` 绑定、Windows 防火墙入站规则和 `/api/health` 自检；验证：README 给出 PowerShell 环境变量示例并能解释局域网访问失败时的排查步骤。
- [x] 1.5 把依赖表中的 `Node.js 20+` 修正为与 `frontend/package.json` 一致的 Node 版本要求，避免 Windows 用户安装不满足 engine 的 Node；验证：README 的 Node 要求与 `frontend/package.json` 的 `engines.node` 一致。

## 2. Windows Report Toolchain

- [x] 2.1 在 `backend/README.md` 增加 Windows 报告工具链说明：TeX Live/MiKTeX、`latexmk`、`xelatex`、ctex/Fandol、`kpsewhich`，并说明 Linux TinyTeX 安装脚本不是原生 Windows 步骤；验证：README 能在 Git Bash/WSL 和原生 Windows 两种路径之间给出明确选择。
- [x] 2.2 说明 Chrome/Chromium 和 PyVista 离屏渲染的 Windows 检查方式，包括 PATH 中 `chrome.exe` 的要求、`/api/health` 的 `chromium`/`offscreen_rendering` 检查，以及失败时报告生成不可用；验证：README 不把“后端能启动”等同于“报告链路可用”。
- [x] 2.3 说明未配置报告依赖时，后端 API、上传、任务和点云下载仍可工作，但 PDF 任务会失败并在 `/api/health` 或任务错误中显式报告；验证：README 明确区分基础运行依赖与报告可选/额外依赖。

## 3. Documentation Verification

- [x] 3.1 在 Windows PowerShell 中按 README 逐条执行环境准备、前端构建、后端启动和 `/api/health`，记录成功输出或具体失败项；验证：README 命令与实际输出一致，失败项不会被描述为已通过。
- [x] 3.2 运行 `git diff --check` 并人工核对 `backend/README.md`，确认没有修改后端代码、依赖、Linux 启动语义或无关文件；验证：变更范围只包含文档和本次 OpenSpec artifacts。
- [x] 3.3 运行 `openspec validate document-windows-backend-setup --strict`，确认 planning artifacts 结构有效；验证：命令返回通过且没有缺失 artifact 或无效 spec。
