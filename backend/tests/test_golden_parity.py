"""任务 2.3：golden 基线对比（新实现 vs base_software 基线）。

对比策略：
- 确定性函数：逐点完全一致（容差 0）。
- 泊松圆盘采样：Open3D 内部随机采样，无法逐点一致；此处显式声明容差，
  比较点数、质心、包围盒与平均最近邻间距。
- FPFH-RANSAC：随机全局配准，重复运行偶尔落到不同局部最优；按"配准质量"
  （到固定点云的平均最近邻距离）声明容差对比。
- 已知边界行为（Point2Plane 邻域不足记 0、find_r 空结果抛错）按原样保留并断言。
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.neighbors import KDTree

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(REPO_ROOT / "base_software"))

from functions import FPFH as base_fpfh_module  # noqa: E402
from functions import down_samples as base_down  # noqa: E402
from functions import knn as base_knn  # noqa: E402
from functions import load_data as base_load  # noqa: E402
from functions.FPFH import FPFH_Registration as base_fpfh  # noqa: E402
from functions.Poisson_Disk_Sampling import Mesh_to_PCD as base_mesh  # noqa: E402
from functions.Registration import Open3d_ICP as base_icp  # noqa: E402

from app.algos import FPFH as new_fpfh_module  # noqa: E402
from app.algos import down_samples as new_down  # noqa: E402
from app.algos import knn as new_knn  # noqa: E402
from app.algos import load_data as new_load  # noqa: E402
from app.algos import units as new_units  # noqa: E402
from app.algos.FPFH import FPFH_Registration as new_fpfh  # noqa: E402
from app.algos.Poisson_Disk_Sampling import Mesh_to_PCD as new_mesh  # noqa: E402
from app.algos.Registration import Open3d_ICP as new_icp  # noqa: E402

SCENE = FIXTURES / "sample_scene.xyz"
BIM = FIXTURES / "sample_bim.xyz"
MESH = FIXTURES / "sample_mesh.ply"


def test_load_data_parity() -> None:
    assert np.array_equal(new_load.data_load(str(SCENE)), base_load.data_load(str(SCENE)))


def test_scale_points_matches_baseline_formula() -> None:
    points = np.array([[1.0, -2.0, 3.5], [0.0, 0.5, -1.0]])
    dictionary = {"m": 1, "dm": 0.1, "cm": 0.01, "mm": 0.001}  # 基线页面 Dictionary
    for origin in dictionary:
        for target in dictionary:
            expected = points * float(dictionary[origin] / dictionary[target])
            assert np.array_equal(new_units.scale_points(points, origin, target), expected)
    with pytest.raises(KeyError):
        new_units.scale_points(points, "m", "km")


def test_downsample_parity() -> None:
    scene = base_load.data_load(str(SCENE))
    assert np.array_equal(new_down.voxel_downsample(scene, 0.15), base_down.voxel_downsample(scene, 0.15))
    assert np.array_equal(new_down.uniform_downsample(scene, 3), base_down.uniform_downsample(scene, 3))


def test_mesh_to_pcd_declared_tolerance() -> None:
    base_pts = base_mesh(str(MESH), 0.2)
    new_pts = new_mesh(str(MESH), 0.2)

    # 点数由表面积与点间距决定，必须一致
    assert len(new_pts) == len(base_pts)

    # 显式声明容差：泊松采样位置随机（不超过目标间距的 25%）
    spacing = 0.2
    assert np.linalg.norm(new_pts.mean(axis=0) - base_pts.mean(axis=0)) < spacing * 0.25
    assert np.allclose(np.ptp(new_pts, axis=0), np.ptp(base_pts, axis=0), atol=spacing * 0.25)

    def mean_nn_distance(points: np.ndarray) -> float:
        distances, _ = KDTree(points).query(points, k=2)
        return float(distances[:, 1].mean())

    assert abs(mean_nn_distance(new_pts) - mean_nn_distance(base_pts)) < spacing * 0.1


def _mean_nn_to_reference(points: np.ndarray, reference: np.ndarray) -> float:
    distances, _ = KDTree(reference).query(points, k=1)
    return float(distances.mean())


def test_fpfh_algorithm_source_identical_to_baseline() -> None:
    """FPFH-RANSAC 为随机算法（重复运行会落到不同局部最优），无法逐点/逐次对比。

    因此先验证"搬运未改动实现"：与基线相比，三个函数的源码逐字一致。
    """
    import inspect
    import textwrap

    for name in ("preprocess_point_cloud", "execute_global_registration", "FPFH_Registration"):
        base_src = textwrap.dedent(inspect.getsource(getattr(base_fpfh_module, name)))
        new_src = textwrap.dedent(inspect.getsource(getattr(new_fpfh_module, name)))
        assert new_src == base_src, f"{name} 源码与基线不一致"


def test_fpfh_registration_quality_contract() -> None:
    """行为层验证：单次运行应显著优于未配准基线。

    实测（各 20 次）：未配准 fitness=0.07634；基线注册 0.06591~0.06996（均值 0.06764）、
    新实现 0.06718~0.06996（均值 0.06757），两实现分布统计等价；随机波动使逐次对比不可行，
    这里以"优于未配准 × 0.98"（阈值 0.0748，实测最差 0.06996 仍有 6.9% 余量）作为质量契约。
    """
    reference = base_load.data_load(str(BIM))
    unregistered = base_load.data_load(str(SCENE))
    threshold = _mean_nn_to_reference(unregistered, reference) * 0.98

    for runner in (base_fpfh, new_fpfh):
        points = runner(str(SCENE), str(BIM), 0.2)
        assert points.shape == unregistered.shape
        assert _mean_nn_to_reference(points, reference) < threshold


def test_icp_parity() -> None:
    scene, bim = base_load.data_load(str(SCENE)), base_load.data_load(str(BIM))
    # 显式声明容差：同上（基线自身重跑差异 ~4.4e-16，新旧差异 ~6.7e-16）。
    assert np.allclose(new_icp(scene, bim, 0.1), base_icp(scene, bim, 0.1), rtol=1e-12, atol=1e-12)


def test_knn_search_parity() -> None:
    scene, bim = base_load.data_load(str(SCENE)), base_load.data_load(str(BIM))
    check = bim[:120]
    assert np.array_equal(new_knn.find_k(check, scene, 1), base_knn.find_k(check, scene, 1))
    assert np.array_equal(new_knn.find_r(check, scene, 0.2), base_knn.find_r(check, scene, 0.2))


def test_point2point_error_parity() -> None:
    scene, bim = base_load.data_load(str(SCENE)), base_load.data_load(str(BIM))
    check = bim[:150]
    assert np.array_equal(
        new_knn.Error_caculate_Point2Point(check, scene, 1),
        base_knn.Error_caculate_Point2Point(check, scene, 1),
    )


def test_point2plane_error_parity() -> None:
    scene, bim = base_load.data_load(str(SCENE)), base_load.data_load(str(BIM))
    check = bim[:150]
    assert np.array_equal(
        new_knn.Error_caculate_Point2Plane(check, scene, 0.2),
        base_knn.Error_caculate_Point2Plane(check, scene, 0.2),
    )


def test_point2plane_sparse_neighborhood_keeps_zero_behavior() -> None:
    sparse = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]])
    check = np.array([[5.0, 5.0, 5.0], [10.0, -3.0, 2.0]])
    base_err = base_knn.Error_caculate_Point2Plane(check, sparse, 0.05)
    new_err = new_knn.Error_caculate_Point2Plane(check, sparse, 0.05)
    assert np.array_equal(new_err, base_err)
    assert np.all(new_err == 0)  # 邻域不足按原实现记 0（行为保留）


def test_find_r_empty_result_raises_same_error() -> None:
    sparse = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    check = np.array([[100.0, 100.0, 100.0]])
    with pytest.raises(ValueError):
        base_knn.find_r(check, sparse, 0.01)
    with pytest.raises(ValueError):
        new_knn.find_r(check, sparse, 0.01)
