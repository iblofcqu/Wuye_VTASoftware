"""配准服务：FPFH 粗配准与三连 ICP 精配准（语义与基线页面一致）。"""

from pathlib import Path

import numpy as np

from app.algos.FPFH import FPFH_Registration
from app.algos.Registration import Open3d_ICP
from app.algos.load_data import data_load
from app.services.common import (
    ProgressCallback,
    ToolResult,
    baseline_stem,
    noop_progress,
    require_positive_number,
)

ICP_DEFAULT_THRESHOLDS = (0.05, 0.03, 0.005)  # 基线页面精配准默认阈值


def register_fpfh(
    moving_path, fixed_path, output_dir, *, voxel_size, progress: ProgressCallback | None = None
) -> ToolResult:
    progress = progress or noop_progress
    voxel_size = require_positive_number(voxel_size, "体素大小")
    moving_path, fixed_path, output_dir = Path(moving_path), Path(fixed_path), Path(output_dir)

    progress("FPFH 粗配准", 1, 2)
    points = FPFH_Registration(str(moving_path), str(fixed_path), voxel_size)

    progress("保存结果", 2, 2)
    output_path = output_dir / f"{baseline_stem(moving_path)}_FPFH.xyz"
    np.savetxt(output_path, points)
    return ToolResult(
        output_path=output_path,
        display_name=output_path.name,
        summary={"point_count": int(len(points)), "voxel_size": voxel_size},
    )


def register_icp(
    moving_path,
    fixed_path,
    output_dir,
    *,
    thresholds=ICP_DEFAULT_THRESHOLDS,
    progress: ProgressCallback | None = None,
) -> ToolResult:
    progress = progress or noop_progress
    try:
        values = [float(value) for value in thresholds]
    except (TypeError, ValueError):
        raise ValueError("ICP 阈值必须是数值") from None
    if len(values) != 3:
        raise ValueError("ICP 精配准需要三个阈值")
    for index, value in enumerate(values, 1):
        require_positive_number(value, f"第{index}次精配阈值")
    moving_path, fixed_path, output_dir = Path(moving_path), Path(fixed_path), Path(output_dir)

    progress("读取点云", 1, 5)
    moving = data_load(str(moving_path))
    fixed = data_load(str(fixed_path))

    points = moving
    for index, threshold in enumerate(values, 1):
        points = Open3d_ICP(points, fixed, threshold)
        progress(f"第{index}/3次 ICP（阈值 {threshold}）", 1 + index, 5)

    progress("保存结果", 5, 5)
    output_path = output_dir / f"{baseline_stem(moving_path)}_ICP.xyz"
    np.savetxt(output_path, points)
    return ToolResult(
        output_path=output_path,
        display_name=output_path.name,
        summary={"point_count": int(len(points)), "thresholds": values},
    )
