"""任务 2.2 验证：报告模块不依赖 streamlit/stpyvista，可生成样例图片与 LaTeX 源。"""

import importlib.util
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image
from pylatex import Document

from app.report import figures, pdf


def _make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    scene = rng.random((400, 3)) * 2.0
    bim = rng.random((500, 3)) * 2.0
    check = scene.copy()
    error = rng.random(len(check)) * 3.0
    return scene, bim, check, error


def test_report_images_generated(tmp_path: Path) -> None:
    scene, bim, check, error = _make_data()
    figures.draw1(tmp_path / "fig1a.jpg", scene, 1, "red")
    figures.draw1(tmp_path / "fig1b.jpg", bim, 1, "blue")
    figures.draw2(tmp_path / "fig2.jpg", scene, bim, 1, 1, "red", "blue")
    figures.draw1(tmp_path / "fig3.jpg", scene, 1, "red")
    figures.draw1(tmp_path / "fig4.jpg", check, 1, "blue")
    figures.draw_error2(tmp_path / "fig5.jpg", check, error, 2, 0.1)

    error_sorted = sorted(error * 1000, reverse=True)
    cut_line = error_sorted[int(len(error_sorted) * 0.1)]
    fig = figures.show_clum(error_sorted, step=1, ratio=0.1, cut_line=cut_line, IS=4)
    fig.write_image(tmp_path / "Error_Analysis.jpg", format="png", scale=2)

    for name in (
        "fig1a.jpg",
        "fig1b.jpg",
        "fig2.jpg",
        "fig3.jpg",
        "fig4.jpg",
        "fig5.jpg",
        "Error_Analysis.jpg",
    ):
        path = tmp_path / name
        assert path.exists(), f"{name} 未生成"
        assert path.stat().st_size > 1000, f"{name} 文件过小"


def test_latex_source_generated_without_tex(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    out_dir = tmp_path / "out"
    cache_dir.mkdir()
    out_dir.mkdir()
    for name in (
        "fig1a.jpg",
        "fig1b.jpg",
        "fig2.jpg",
        "fig3.jpg",
        "fig4.jpg",
        "fig5.jpg",
        "Error_Analysis.jpg",
    ):
        Image.new("RGB", (32, 32), "white").save(cache_dir / name)

    info = {
        "PCD_name": "SCAN",
        "SCENE_path": "/data/scan.xyz",
        "BIM_path": "/data/bim.xyz",
        "unit": "m",
        "method": "Point2Point",
        "distance": 0.1,
        "ratio": 0.05,
        "len_pcd_scene": 1000,
        "len_pcd_bim": 2000,
        "check_num": 900,
        "error_max_cut": 12.34,
        "error_max": 20.0,
        "error_mean": 5.67,
    }

    def fake_generate_pdf(self: Document, filename: str, *args: object, **kwargs: object) -> None:
        self.generate_tex(filename)

    with mock.patch.object(Document, "generate_pdf", fake_generate_pdf):
        pdf.QA_Report(str(cache_dir), str(out_dir), info)

    tex_files = list(out_dir.glob("*.tex"))
    assert len(tex_files) == 1, f"未生成 LaTeX 源: {tex_files}"
    content = tex_files[0].read_text(encoding="utf-8")
    assert "ctex" in content
    assert "几何质量评估报告" in content
    assert "fig5.jpg" in content
    assert "Error_Analysis.jpg" in content


def test_backend_has_no_streamlit_dependency() -> None:
    assert importlib.util.find_spec("streamlit") is None
    assert importlib.util.find_spec("stpyvista") is None
