"""任务 2.4：预处理服务的输出命名、数值与参数校验。"""

from pathlib import Path

import numpy as np
import pytest

from app.algos import load_data
from app.algos.down_samples import uniform_downsample
from app.algos.units import UNIT_TO_METER
from app.services import preprocessing

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCENE = FIXTURES / "sample_scene.xyz"
MESH = FIXTURES / "sample_mesh.ply"


def test_grid_discretize_outputs_named_xyz(tmp_path: Path) -> None:
    events: list[tuple] = []
    result = preprocessing.grid_discretize(
        MESH, tmp_path, distance_points=0.3, progress=lambda *args: events.append(args)
    )
    assert result.output_path == tmp_path / "sample_mesh.xyz"
    assert result.display_name == "sample_mesh.xyz"
    points = np.loadtxt(result.output_path)
    assert result.summary["point_count"] == len(points) > 0
    assert [(e[1], e[2]) for e in events] == [(1, 2), (2, 2)]


def test_scale_outputs_target_suffix_and_values(tmp_path: Path) -> None:
    result = preprocessing.scale(SCENE, tmp_path, origin_unit="m", target_unit="mm")
    assert result.output_path.name == "sample_scene_mm.xyz"
    expected = load_data.data_load(str(SCENE)) * float(UNIT_TO_METER["m"] / UNIT_TO_METER["mm"])
    assert np.array_equal(np.loadtxt(result.output_path), expected)
    assert result.summary["coefficient"] == float(UNIT_TO_METER["m"] / UNIT_TO_METER["mm"])


def test_downsample_voxel_naming_and_counts(tmp_path: Path) -> None:
    result = preprocessing.downsample_voxel(SCENE, tmp_path, voxel_size=0.1)
    assert result.output_path.name == "sample_scene_VD.xyz"
    assert result.summary["input_point_count"] == len(load_data.data_load(str(SCENE)))
    assert 0 < result.summary["point_count"] < result.summary["input_point_count"]


def test_downsample_uniform_naming_and_values(tmp_path: Path) -> None:
    result = preprocessing.downsample_uniform(SCENE, tmp_path, every_k=2)
    assert result.output_path.name == "sample_scene_UD.xyz"
    expected = uniform_downsample(load_data.data_load(str(SCENE)), 2)
    assert np.array_equal(np.loadtxt(result.output_path), expected)


@pytest.mark.parametrize("bad", [0, -1, "abc", None, float("nan")])
def test_grid_discretize_rejects_bad_distance(tmp_path: Path, bad: object) -> None:
    with pytest.raises(ValueError, match="点云间距"):
        preprocessing.grid_discretize(MESH, tmp_path, distance_points=bad)


@pytest.mark.parametrize("bad", [0, -0.1, "abc", None])
def test_voxel_rejects_bad_size(tmp_path: Path, bad: object) -> None:
    with pytest.raises(ValueError, match="体素尺寸"):
        preprocessing.downsample_voxel(SCENE, tmp_path, voxel_size=bad)


@pytest.mark.parametrize("bad", [0, -2, 1.5, "abc", None])
def test_uniform_rejects_bad_interval(tmp_path: Path, bad: object) -> None:
    with pytest.raises(ValueError, match="采样间隔"):
        preprocessing.downsample_uniform(SCENE, tmp_path, every_k=bad)


def test_scale_rejects_unknown_unit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="未知单位"):
        preprocessing.scale(SCENE, tmp_path, origin_unit="m", target_unit="km")
