"""运行配置（环境变量可覆盖）。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # 仓库根目录
DATA_DIR = Path(os.environ.get("WUYE_DATA_DIR", BASE_DIR / "data"))
SESSION_ROOT = DATA_DIR / "sessions"

SESSION_COOKIE_NAME = os.environ.get("WUYE_SESSION_COOKIE", "wuye_session")
SESSION_MAX_AGE_SECONDS = int(os.environ.get("WUYE_SESSION_MAX_AGE_SECONDS", str(30 * 24 * 3600)))
