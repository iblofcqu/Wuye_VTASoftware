"""任务 2.6：质量评估服务的数值一致性、报告命名与产物完整性。"""

import json
import time
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from pylatex import Document

from app.algos import load_data
from app.algos.down_samples import voxel_downsample
from app.algos.knn import Error_caculate_Point2Plane, Error_caculate_Point2Point, find_k, find_r
from app.report import figures
from app.services import quality

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENE = FIXTURES / "sample_scene.xyz"
BIM = FIXTURES / "sample_bim.xyz"


def _baseline_errors(method: str, distance: float) -> tuple[np.ndarray, np.ndarray]:
    scene = load_data.data_load(str(SCENE))
    bim = load_data.data_load(str(BIM))
    bim_down = voxel_downsample(bim, quality.QA_BIM_DOWNSAMPLE_VOXEL)
    clean = find_r(bim_down, scene, r=distance * 10)
    check = find_k(clean, bim, k=1)
    if method == "Point2Point":
        error = Error_caculate_Point2Point(check, clean, k=1)
    else:
        error = Error_caculate_Point2Plane(check, clean, r=distance)
    return check, error


def _fake_compile(self: Document, filename: str, *args: object, **kwargs: object) -> None:
    self.generate_tex(filename)


@pytest.mark.parametrize("method", ["Point2Point", "Point2Plane"])
def test_assess_matches_baseline_and_report_naming(tmp_path: Path, method: str) -> None:
    cache_dir, out_dir = tmp_path / "cache", tmp_path / "out"
    cache_dir.mkdir()
    out_dir.mkdir()

    distance = 0.05 if method == "Point2Point" else 0.2
    events: list[tuple] = []
    with mock.patch.object(Document, "generate_pdf", _fake_compile):
        result = quality.assess(
            SCENE,
            BIM,
            out_dir,
            cache_dir,
            unit="m",
            method=method,
            distance=distance,
            ratio=0.05,
            progress=lambda *args: events.append(args),
        )

    check, error = _baseline_errors(method, distance)
    saved = np.load(cache_dir / "error_cloud.npy")
    assert np.array_equal(saved[:, :3], check)
    assert np.array_equal(saved[:, 3], error)

    error_sorted = sorted(error * 1000, reverse=True)
    line = float(error_sorted[int(len(error_sorted) * 0.05)])
    assert result.summary["check_num"] == len(error_sorted)
    assert result.summary["error_max_cut"] == float(f"{line:.2f}")
    assert result.summary["error_max"] == float(f"{max(error_sorted):.2f}")
    assert result.summary["error_mean"] == float(f"{np.mean(error_sorted):.2f}")
    assert result.summary["method"] == method
    assert result.summary["figure"]["data"], "histogram figure 数据缺失"
    ui_figure = result.summary["ui_figure"]
    assert ui_figure["data"], "browser histogram figure 数据缺失"
    assert len(ui_figure["data"][0]["x"]) <= figures.UI_HISTOGRAM_MAX_BARS
    assert len(ui_figure["layout"]["xaxis"].get("tickvals", [])) <= figures.UI_HISTOGRAM_MAX_TICKS
    assert ui_figure["layout"]["shapes"][0]["x0"] == pytest.approx(line)

    t = time.localtime()
    expected_stem = f"sample_scene几何质量评估报告{t[0]}{t[1]}{t[2]}"
    assert result.output_path.name == f"{expected_stem}.pdf"
    assert (out_dir / f"{expected_stem}.tex").exists(), "LaTeX 源未生成"

    for name in (
        "fig1a.jpg",
        "fig1b.jpg",
        "fig2.jpg",
        "fig3.jpg",
        "fig4.jpg",
        "fig5.jpg",
        "Error_Analysis.jpg",
    ):
        assert (cache_dir / name).stat().st_size > 1000, f"{name} 缺失或过小"

    assert [(e[1], e[2]) for e in events] == [(1, 4), (2, 4), (3, 4), (4, 4)]


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(unit="km", method="Point2Point", distance=0.05, ratio=0.05),
        dict(unit="m", method="Foo", distance=0.05, ratio=0.05),
        dict(unit="m", method="Point2Point", distance=0, ratio=0.05),
        dict(unit="m", method="Point2Point", distance="abc", ratio=0.05),
        dict(unit="m", method="Point2Point", distance=0.05, ratio=1),
        dict(unit="m", method="Point2Point", distance=0.05, ratio=-0.1),
        dict(unit="m", method="Point2Point", distance=0.05, ratio="abc"),
    ],
)
def test_assess_rejects_bad_params(tmp_path: Path, kwargs: dict) -> None:
    cache_dir, out_dir = tmp_path / "cache", tmp_path / "out"
    cache_dir.mkdir()
    out_dir.mkdir()
    with pytest.raises(ValueError):
        quality.assess(SCENE, BIM, out_dir, cache_dir, **kwargs)


def _figure_counts(payload: dict) -> tuple[int, int]:
    return len(payload["data"][0]["x"]), len(payload["layout"]["xaxis"].get("tickvals", []))


def test_ui_histogram_bounds_large_range_and_preserves_statistics() -> None:
    error_sorted = sorted(np.linspace(0, 5347.33, 940), reverse=True)
    line = float(error_sorted[int(len(error_sorted) * 0.05)])
    step, tick_stride = figures.ui_histogram_params(error_sorted)
    figure = figures.show_clum(
        error_sorted, step=step, ratio=0.05, cut_line=line, IS=tick_stride
    )
    payload = json.loads(figure.to_json())

    bars, ticks = _figure_counts(payload)
    assert bars <= figures.UI_HISTOGRAM_MAX_BARS
    assert ticks <= figures.UI_HISTOGRAM_MAX_TICKS
    assert payload["layout"]["shapes"][0]["x0"] == pytest.approx(line)
    annotation = payload["layout"]["annotations"][-1]["text"]
    assert f"最大值: {max(error_sorted):.2f}" in annotation
    assert f"平均值: {np.mean(error_sorted):.2f}" in annotation


def test_ui_histogram_handles_zero_error_result() -> None:
    error_sorted = [0.0] * 940
    step, tick_stride = figures.ui_histogram_params(error_sorted)
    figure = figures.show_clum(
        error_sorted, step=step, ratio=0.05, cut_line=0.0, IS=tick_stride
    )
    payload = json.loads(figure.to_json())

    bars, ticks = _figure_counts(payload)
    assert (bars, ticks) == (0, 0)
