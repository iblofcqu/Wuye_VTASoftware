# DeviScan-3D B/S 后端（FastAPI）

## 依赖安装清单（Linux）

| 依赖 | 用途 | 安装 |
| --- | --- | --- |
| uv + Python 3.10.18 | 后端运行（uv 按 `.python-version` 自动安装） | 见 <https://docs.astral.sh/uv/>；`cd backend && uv sync --frozen` |
| Node.js 22.18+ 或 >=24.12.0 | 构建前端静态资源（仅构建期；与 `frontend/package.json` engines 一致） | 系统包管理器或 nvm |
| TeX Live / TinyTeX（含 ctex + Fandol 字体） | PDF 报告编译（latexmk + xelatex） | 见 [docs/report-toolchain.md](docs/report-toolchain.md) |
| Chrome / Chromium | kaleido 导出直方图图片 | `apt install chromium` 或已有 Chrome |
| 离屏渲染支持 | pyvista 报告截图 | 有 DISPLAY 即可；无显示环境用 xvfb-run 或 EGL/OSMesa |
| 中文字体 | 报告与页面中文显示 | 随 ctex/Fandol 宏包提供 |

启动前自检：`curl http://<host>:<port>/api/health`（四项依赖逐项报告）。

## 构建与启动

```bash
# 1) 构建前端（首次或前端变更后）
cd frontend && npm ci && npm run build

# 2) 启动后端（同源托管 frontend/dist）
PORT=8000 backend/scripts/start.sh
```

浏览器访问 `http://<服务器IP>:8000/`；API 文档在 `/docs`。

## Windows 平台配置

以下步骤面向 Windows 10/11 + PowerShell。后端仍通过 uv 管理 Python 依赖，**不要**直接把 Linux 的 `.sh` 启动命令当成 PowerShell 命令执行。

### 1. 安装并检查运行依赖

- 安装 **uv**（官方安装说明：<https://docs.astral.sh/uv/getting-started/installation/>），然后在 PowerShell 中确认：

  ```powershell
  uv --version
  uv python install 3.10.18
  ```

- 安装 **Node.js 22.18+ 或 >=24.12.0**（官方下载：<https://nodejs.org/en/download>）。该范围与 `frontend/package.json` 的 `engines.node` 一致；Node 20 不满足前端构建要求。

  ```powershell
  node --version
  npm --version
  ```

- 如果只运行 API、不上传 PDF 报告，可以先跳过下面的 TeX/Chrome；基础上传、任务和产物下载不依赖报告工具链。

### 2. 构建前端

后端在生产模式下会直接托管 `frontend/dist`。首次运行或前端代码变更后，在仓库根目录执行：

```powershell
cd frontend
npm ci
npm run build
Test-Path .\dist\index.html   # 应返回 True
```

如果 `frontend/dist` 不存在，后端仍能启动 API，但浏览器无法获得完整 SPA。

### 3. 用 PowerShell 启动后端

在仓库根目录执行：

```powershell
cd backend
uv sync --frozen
$env:PORT = "8000"
$env:WUYE_DATA_DIR = "D:\wuye-data"   # 可选；默认是仓库根目录下的 data
uv run uvicorn app.main:app --host 0.0.0.0 --port $env:PORT
```

然后在浏览器访问 `http://127.0.0.1:8000/`，或在 PowerShell 中检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 5
```

### 4. `start.sh` 的 Windows 说明

`backend/scripts/start.sh` 是 Bash 脚本，PowerShell 不能直接运行。可以选择：

- **推荐**：按上面的 PowerShell 命令直接执行 `uv run uvicorn ...`。
- 使用 Git Bash 或 WSL：在仓库根目录执行 `PORT=8000 backend/scripts/start.sh`，并确保 `uv`、Node 和 TeX 工具都能在对应 shell 的 `PATH` 中找到。

WSL 中的路径是 Linux 路径，Git Bash 则是 Windows 路径的兼容层；如果对路径或权限不确定，优先使用 PowerShell 直启方式。

### 5. 环境变量与数据目录

PowerShell 的 `$env:NAME = "value"` 只对当前终端会话生效；需要持久化时使用：

```powershell
[Environment]::SetEnvironmentVariable("WUYE_DATA_DIR", "D:\wuye-data", "User")
```

修改持久环境变量后需要重启终端。`WUYE_DATA_DIR` 必须位于 Windows 可写目录；默认 `data/` 也要求当前用户有写权限。常用变量与默认值见下面的配置表。

### 6. 局域网访问与防火墙

后端绑定 `0.0.0.0` 时，其他机器是否可访问还取决于 Windows 防火墙。仅在可信内网需要放行端口时，使用管理员 PowerShell 添加私网入站规则：

```powershell
New-NetFirewallRule `
  -DisplayName "DeviScan-3D B/S (TCP 8000)" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8000 `
  -Profile Private
```

当前后端无登录和权限系统，只应在可信内网演示；不要把该端口直接暴露到公网。

### 7. Windows 报告工具链

PDF 报告需要额外安装并配置：

- **TeX Live**（<https://tug.org/texlive/windows.html>）或 **MiKTeX**（<https://miktex.org/download>）。
- `latexmk`、`xelatex`、`kpsewhich` 能在 PATH 中找到。
- ctex 与 Fandol 中文字体/宏包；可用以下命令逐项检查：

  ```powershell
  Get-Command latexmk
  Get-Command xelatex
  kpsewhich ctex.sty
  kpsewhich ctex-fontset-fandol.def
  kpsewhich FandolSong-Regular.otf
  ```

Linux/macOS 的 TinyTeX shell 安装脚本不是原生 Windows 步骤；如果使用 TinyTeX，请通过 Git Bash/WSL 安装并把对应 `bin` 目录加入 `PATH`。

Chrome/Chromium 用于 Kaleido 导出直方图图片。安装 Google Chrome 后，Kaleido/choreographer 通常能从 Windows 常见安装位置或注册表发现 Chrome，但当前 `/api/health` 的 `chromium` 检查只搜索 Linux/Chromium 风格的可执行名称，在 Windows 上可能无法识别标准 `chrome.exe`。因此：

- 如果 `/api/health` 报告 `chromium` 失败，但 Chrome 已安装，可直接用一个最小质量评估任务验证报告生成；
- 如果希望 health check 也通过，需要让后端可搜索到它认识的命令名，或后续单独调整 health check；
- 报告任务失败时，以任务错误和 health check 输出为准，不要只根据后端是否启动判断报告链路可用。

PyVista 离屏截图在 Windows 上依赖可用的 OpenGL/显卡驱动。运行 `/api/health`，如果 `offscreen_rendering` 失败，先更新显卡驱动或换到有桌面图形栈的 Windows 会话，再重试报告任务。

未配置 TeX、Chrome 或离屏渲染时，基础 API、上传、任务状态和点云产物下载仍可使用；PDF 报告任务会失败并显式返回原因。

### 8. Windows 最小验收

```powershell
# 基础运行
uv run pytest -q

# 有 TeX/Chrome/离屏渲染时
uv run python tests\e2e_demo_checklist.py
```

Windows 上不要使用 Linux 的 `PATH="$HOME/.local/bin:$PATH"` 写法；请把 TeX 的 bin 目录加入 Windows 用户/系统 `PATH` 后重启 PowerShell，或临时执行：

```powershell
$env:Path = "C:\path\to\tex\bin;$env:Path"
```

报告链路是否完整以 `/api/health` 和端到端清单的实际结果为准。

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `WUYE_DATA_DIR` | `<repo>/data` | 会话与产物数据目录 |
| `WUYE_SESSION_MAX_AGE_SECONDS` | 2592000（30 天） | 会话 cookie 有效期 |
| `WUYE_JOB_POOL_SIZE` | 2 | 计算进程池容量 |
| `WUYE_PREVIEW_MAX_POINTS` | 1000000 | 预览点数上限 |
| `WUYE_REPORT_TIMEOUT_SECONDS` | 300 | 报告生成阶段超时秒数（30~3600）；超时任务失败并报告最后阶段 |
| `WUYE_MAX_UPLOAD_BYTES` | 5 GiB | 单文件大小上限 |
| `WUYE_UPLOAD_CHUNK_SIZE` | 8 MiB | 默认分片大小 |
| `WUYE_UPLOAD_TTL_SECONDS` | 86400 | 未完成上传保留时间 |
| `PORT` | 8000 | 服务端口（启动脚本） |

## 测试

```bash
cd backend
uv run pytest -q                      # 全部后端测试
PATH="$HOME/.local/bin:$PATH" uv run pytest -q   # 含真实 PDF 报告链路
```

质量评估的报告生成阶段默认有 5 分钟超时；超时后任务会失败、不会登记 PDF 产物，错误信息包含超时秒数和最后阶段。Windows/PowerShell 使用同一 `WUYE_REPORT_TIMEOUT_SECONDS` 环境变量。
