"""运行配置（环境变量可覆盖）。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # 仓库根目录
DATA_DIR = Path(os.environ.get("WUYE_DATA_DIR", BASE_DIR / "data"))
SESSION_ROOT = DATA_DIR / "sessions"

SESSION_COOKIE_NAME = os.environ.get("WUYE_SESSION_COOKIE", "wuye_session")
SESSION_MAX_AGE_SECONDS = int(os.environ.get("WUYE_SESSION_MAX_AGE_SECONDS", str(30 * 24 * 3600)))

# 断点续传上传
MAX_UPLOAD_BYTES = int(os.environ.get("WUYE_MAX_UPLOAD_BYTES", str(5 * 1024 ** 3)))
UPLOAD_CHUNK_SIZE = int(os.environ.get("WUYE_UPLOAD_CHUNK_SIZE", str(8 * 1024 * 1024)))
UPLOAD_MIN_CHUNK_SIZE = int(os.environ.get("WUYE_UPLOAD_MIN_CHUNK_SIZE", str(1024)))
UPLOAD_MAX_CHUNK_SIZE = int(os.environ.get("WUYE_UPLOAD_MAX_CHUNK_SIZE", str(64 * 1024 * 1024)))
UPLOAD_TTL_SECONDS = int(os.environ.get("WUYE_UPLOAD_TTL_SECONDS", str(24 * 3600)))

# 任务执行
JOB_POOL_SIZE = int(os.environ.get("WUYE_JOB_POOL_SIZE", "2"))
JOB_WORK_DIR = "work"

# 预览
PREVIEW_MAX_POINTS = int(os.environ.get("WUYE_PREVIEW_MAX_POINTS", "1000000"))
