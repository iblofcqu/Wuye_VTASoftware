"""点云预处理服务：网格离散、尺寸缩放、体素/均匀下采样。

参数校验与输出命名与 base_software 页面语义一致；非法参数显式抛 ValueError。
"""

from pathlib import Path

import numpy as np

from app.algos.Poisson_Disk_Sampling import Mesh_to_PCD
from app.algos.down_samples import uniform_downsample, voxel_downsample
from app.algos.load_data import data_load
from app.algos.units import UNIT_TO_METER, scale_points
from app.services.common import (
    ProgressCallback,
    ToolResult,
    baseline_stem,
    noop_progress,
    require_positive_int,
    require_positive_number,
)


def grid_discretize(
    input_path,
    output_dir,
    *,
    distance_points,
    input_name: str | None = None,
    progress: ProgressCallback | None = None,
) -> ToolResult:
    progress = progress or noop_progress
    distance = require_positive_number(distance_points, "点云间距")
    input_path, output_dir = Path(input_path), Path(output_dir)

    progress("读取网格并离散", 1, 2)
    points = Mesh_to_PCD(str(input_path), distance)

    progress("保存结果", 2, 2)
    output_path = output_dir / f"{baseline_stem(input_name or input_path)}.xyz"
    np.savetxt(output_path, points)
    return ToolResult(
        output_path=output_path,
        display_name=output_path.name,
        summary={"point_count": int(len(points))},
    )


def scale(
    input_path,
    output_dir,
    *,
    origin_unit: str,
    target_unit: str,
    input_name: str | None = None,
    progress: ProgressCallback | None = None,
) -> ToolResult:
    progress = progress or noop_progress
    for unit in (origin_unit, target_unit):
        if unit not in UNIT_TO_METER:
            raise ValueError(f"未知单位: {unit}")
    input_path, output_dir = Path(input_path), Path(output_dir)

    progress("读取点云", 1, 3)
    points = data_load(str(input_path))

    progress("单位换算", 2, 3)
    coefficient = float(UNIT_TO_METER[origin_unit] / UNIT_TO_METER[target_unit])
    scaled = scale_points(points, origin_unit, target_unit)

    progress("保存结果", 3, 3)
    output_path = output_dir / f"{baseline_stem(input_name or input_path)}_{target_unit}.xyz"
    np.savetxt(output_path, scaled)
    return ToolResult(
        output_path=output_path,
        display_name=output_path.name,
        summary={"point_count": int(len(scaled)), "coefficient": coefficient},
    )


def downsample_voxel(
    input_path,
    output_dir,
    *,
    voxel_size,
    input_name: str | None = None,
    progress: ProgressCallback | None = None,
) -> ToolResult:
    progress = progress or noop_progress
    voxel_size = require_positive_number(voxel_size, "体素尺寸")
    input_path, output_dir = Path(input_path), Path(output_dir)

    progress("读取点云", 1, 3)
    points = data_load(str(input_path))

    progress("体素下采样", 2, 3)
    downsampled = voxel_downsample(points, voxel_size)

    progress("保存结果", 3, 3)
    output_path = output_dir / f"{baseline_stem(input_name or input_path)}_VD.xyz"
    np.savetxt(output_path, downsampled)
    return ToolResult(
        output_path=output_path,
        display_name=output_path.name,
        summary={"input_point_count": int(len(points)), "point_count": int(len(downsampled))},
    )


def downsample_uniform(
    input_path,
    output_dir,
    *,
    every_k,
    input_name: str | None = None,
    progress: ProgressCallback | None = None,
) -> ToolResult:
    progress = progress or noop_progress
    every_k = require_positive_int(every_k, "采样间隔")
    input_path, output_dir = Path(input_path), Path(output_dir)

    progress("读取点云", 1, 3)
    points = data_load(str(input_path))

    progress("均匀下采样", 2, 3)
    downsampled = uniform_downsample(points, every_k)

    progress("保存结果", 3, 3)
    output_path = output_dir / f"{baseline_stem(input_name or input_path)}_UD.xyz"
    np.savetxt(output_path, downsampled)
    return ToolResult(
        output_path=output_path,
        display_name=output_path.name,
        summary={"input_point_count": int(len(points)), "point_count": int(len(downsampled))},
    )
