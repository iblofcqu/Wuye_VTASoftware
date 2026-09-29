"""任务 2.6：质量评估服务的数值一致性、报告命名与产物完整性。"""

import time
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from pylatex import Document

from app.algos import load_data
from app.algos.down_samples import voxel_downsample
from app.algos.knn import Error_caculate_Point2Plane, Error_caculate_Point2Point, find_k, find_r
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
