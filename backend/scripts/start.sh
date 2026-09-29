#!/usr/bin/env bash
# 启动 DeviScan-3D B/S 后端（同源托管 frontend/dist）。
# 用法: PORT=8000 backend/scripts/start.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${BACKEND_DIR}/.." && pwd)"

# 用户级依赖（TinyTeX 安装到 ~/.local/bin）
export PATH="${HOME}/.local/bin:${PATH}"

cd "${BACKEND_DIR}"

if [ ! -d "${REPO_DIR}/frontend/dist" ]; then
  echo "[warn] 未找到 frontend/dist，前端页面不可用；请先执行: cd frontend && npm ci && npm run build" >&2
fi

uv sync --frozen

echo "[info] 健康检查可访问: http://<host>:${PORT:-8000}/api/health"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
