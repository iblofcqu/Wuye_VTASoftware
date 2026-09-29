"""任务 2.7：报告链路实机验证（latexmk + xelatex + ctex）。

未安装 TeX 时跳过（部署环境由 /api/health 显式检查依赖）。
"""

import shutil
from pathlib import Path

import pytest

from app.services import quality

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENE = FIXTURES / "sample_scene.xyz"
BIM = FIXTURES / "sample_bim.xyz"

pytestmark = pytest.mark.skipif(
    shutil.which("latexmk") is None or shutil.which("xelatex") is None,
    reason="需要 latexmk + xelatex（部署环境由 /api/health 检查）",
)


def test_real_pdf_report_generated(tmp_path: Path) -> None:
    cache_dir, out_dir = tmp_path / "cache", tmp_path / "out"
    cache_dir.mkdir()
    out_dir.mkdir()

    result = quality.assess(
        SCENE,
        BIM,
        out_dir,
        cache_dir,
        unit="m",
        method="Point2Point",
        distance=0.05,
        ratio=0.05,
    )

    pdf_path = result.output_path
    assert pdf_path.exists(), f"PDF 未生成: {pdf_path}"
    data = pdf_path.read_bytes()
    assert data.startswith(b"%PDF"), "不是有效的 PDF 文件"
    assert len(data) > 20_000, f"PDF 过小: {len(data)} bytes"
    assert not list(out_dir.glob("*.tex")), "clean_tex=True 应清理 .tex 中间产物"
