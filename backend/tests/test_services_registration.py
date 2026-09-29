"""任务 2.5：配准服务的输出命名、数值与参数校验。"""

from pathlib import Path

import numpy as np
import pytest

from app.algos import load_data
from app.algos.Registration import Open3d_ICP
from app.services import registration

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENE = FIXTURES / "sample_scene.xyz"
BIM = FIXTURES / "sample_bim.xyz"


def test_register_fpfh_outputs_algorithm_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """服务编排测试：屏蔽随机的 FPFH-RANSAC（算法一致性由 golden 测试覆盖）。"""
    fake = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    monkeypatch.setattr(registration, "FPFH_Registration", lambda *args, **kwargs: fake)

    events: list[tuple] = []
    result = registration.register_fpfh(
        SCENE, BIM, tmp_path, voxel_size=0.2, progress=lambda *args: events.append(args)
    )
    assert result.output_path.name == "sample_scene_FPFH.xyz"
    assert np.array_equal(np.loadtxt(result.output_path), fake)
    assert result.summary["point_count"] == 2
    assert [(e[1], e[2]) for e in events] == [(1, 2), (2, 2)]


def test_register_icp_output_and_parity(tmp_path: Path) -> None:
    thresholds = (0.1, 0.05, 0.02)
    events: list[tuple] = []
    result = registration.register_icp(
        SCENE, BIM, tmp_path, thresholds=thresholds, progress=lambda *args: events.append(args)
    )
    assert result.output_path.name == "sample_scene_ICP.xyz"
    expected = load_data.data_load(str(SCENE))
    fixed = load_data.data_load(str(BIM))
    for threshold in thresholds:
        expected = Open3d_ICP(expected, fixed, threshold)
    assert np.allclose(np.loadtxt(result.output_path), expected, rtol=1e-12, atol=1e-12)
    assert result.summary["thresholds"] == list(thresholds)
    assert [(e[1], e[2]) for e in events] == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]


def test_icp_default_thresholds_match_baseline_page() -> None:
    assert registration.ICP_DEFAULT_THRESHOLDS == (0.05, 0.03, 0.005)


@pytest.mark.parametrize("bad", [0, -1, "abc", None, float("nan")])
def test_register_fpfh_rejects_bad_voxel(tmp_path: Path, bad: object) -> None:
    with pytest.raises(ValueError, match="体素大小"):
        registration.register_fpfh(SCENE, BIM, tmp_path, voxel_size=bad)


@pytest.mark.parametrize(
    "bad",
    [
        (0.05, 0.03),
        (0.05, 0.03, 0.005, 0.001),
        (0.05, -0.03, 0.005),
        (0.05, 0, 0.005),
        (0.05, "x", 0.005),
        None,
    ],
)
def test_register_icp_rejects_bad_thresholds(tmp_path: Path, bad: object) -> None:
    with pytest.raises(ValueError):
        registration.register_icp(SCENE, BIM, tmp_path, thresholds=bad)
