# DeviScan-3D B/S 后端（FastAPI）

## 依赖安装清单（Linux）

| 依赖 | 用途 | 安装 |
| --- | --- | --- |
| uv + Python 3.10.18 | 后端运行（uv 按 `.python-version` 自动安装） | 见 <https://docs.astral.sh/uv/>；`cd backend && uv sync --frozen` |
| Node.js 20+ | 构建前端静态资源（仅构建期） | 系统包管理器或 nvm |
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

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `WUYE_DATA_DIR` | `<repo>/data` | 会话与产物数据目录 |
| `WUYE_SESSION_MAX_AGE_SECONDS` | 2592000（30 天） | 会话 cookie 有效期 |
| `WUYE_JOB_POOL_SIZE` | 2 | 计算进程池容量 |
| `WUYE_PREVIEW_MAX_POINTS` | 1000000 | 预览点数上限 |
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
