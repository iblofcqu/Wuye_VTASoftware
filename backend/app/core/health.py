"""部署依赖自检：TeX、Chromium、离屏渲染与中文字体。"""

import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass

TEX_BINARIES = ("latexmk", "xelatex")
CHROMIUM_BINARIES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
CJK_KPSE_FILES = ("ctex.sty", "ctex-fontset-fandol.def", "FandolSong-Regular.otf")


@dataclass
class HealthCheck:
    name: str
    ok: bool
    detail: str


def check_tex() -> HealthCheck:
    missing = [binary for binary in TEX_BINARIES if shutil.which(binary) is None]
    if missing:
        return HealthCheck("tex", False, f"缺少 TeX 命令: {', '.join(missing)}（见 backend/docs/report-toolchain.md）")
    return HealthCheck("tex", True, "latexmk/xelatex 可用")


def check_chromium() -> HealthCheck:
    for binary in CHROMIUM_BINARIES:
        path = shutil.which(binary)
        if path:
            return HealthCheck("chromium", True, f"已找到 {path}（kaleido 出图）")
    return HealthCheck("chromium", False, "未找到 Chrome/Chromium（kaleido 导出报告图片需要）")


def check_offscreen_rendering() -> HealthCheck:
    try:
        import pyvista as pv
    except Exception as exc:  # pragma: no cover - 依赖缺失场景
        return HealthCheck("offscreen_rendering", False, f"pyvista 不可用: {exc}")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "health.png")
        plotter = pv.Plotter(off_screen=True)
        try:
            plotter.add_mesh(pv.Sphere(theta_resolution=8, phi_resolution=8), color="white")
            plotter.screenshot(path)
        except Exception as exc:
            return HealthCheck("offscreen_rendering", False, f"离屏截图失败: {exc}")
        finally:
            plotter.close()
        ok = os.path.exists(path) and os.path.getsize(path) > 0
    return HealthCheck("offscreen_rendering", True, "pyvista 离屏截图成功")


def check_chinese_fonts() -> HealthCheck:
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        return HealthCheck("chinese_fonts", False, "缺少 kpsewhich（未安装 TeX 发行版）")
    missing = []
    for name in CJK_KPSE_FILES:
        result = subprocess.run([kpsewhich, name], capture_output=True, text=True, timeout=30)
        if result.returncode != 0 or not result.stdout.strip():
            missing.append(name)
    if missing:
        return HealthCheck("chinese_fonts", False, f"缺少中文字体/宏包: {', '.join(missing)}")
    return HealthCheck("chinese_fonts", True, "ctex + Fandol 中文字体可用")


CHECKS = (check_tex, check_chromium, check_offscreen_rendering, check_chinese_fonts)


def run_health_checks(checks=None) -> list[dict]:
    results: list[dict] = []
    for check in checks or CHECKS:
        try:
            results.append(asdict(check()))
        except Exception as exc:  # noqa: BLE001 - 自检异常也要显式上报
            results.append({"name": check.__name__, "ok": False, "detail": f"检查异常: {exc}"})
    return results
