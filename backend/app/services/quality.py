"""尺寸质量评估服务：偏差计算、统计、直方图数据与 PDF 报告（语义与基线页面一致）。"""

import json
import time
from pathlib import Path

import numpy as np

from app.algos.down_samples import voxel_downsample
from app.algos.knn import Error_caculate_Point2Plane, Error_caculate_Point2Point, find_k, find_r
from app.algos.load_data import data_load
from app.algos.units import UNIT_TO_METER
from app.report import figures, pdf
from app.services.common import (
    ProgressCallback,
    ReportProgressCallback,
    ToolResult,
    baseline_stem,
    noop_progress,
    noop_report_progress,
    require_positive_number,
)

QA_METHODS = ("Point2Point", "Point2Plane")
QA_BIM_DOWNSAMPLE_VOXEL = 0.1  # 基线页面固定体素尺寸


def _parse_ratio(ratio) -> float:
    try:
        value = float(ratio)
    except (TypeError, ValueError):
        raise ValueError("剔除比例必须是数值") from None
    if not (0 <= value < 1):
        raise ValueError("剔除比例必须在 [0, 1) 区间")
    return value


def assess(
    scene_path,
    bim_path,
    output_dir,
    cache_dir,
    *,
    unit,
    method,
    distance,
    ratio,
    scan_name: str | None = None,
    progress: ProgressCallback | None = None,
    report_progress: ReportProgressCallback | None = None,
) -> ToolResult:
    progress = progress or noop_progress
    report_progress = report_progress or noop_report_progress
    if unit not in UNIT_TO_METER:
        raise ValueError(f"未知单位: {unit}")
    if method not in QA_METHODS:
        raise ValueError(f"未知偏差计算方法: {method}")
    distance = require_positive_number(distance, "平面邻域大小")
    ratio_value = _parse_ratio(ratio)

    scene_path, bim_path = Path(scene_path), Path(bim_path)
    output_dir, cache_dir = Path(output_dir), Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)  # 基线的 get_cache_path() 会自动创建缓存目录
    name = baseline_stem(scan_name or scene_path)

    progress("第1/4步 文件读取", 1, 4)
    pcd_scene = data_load(str(scene_path))
    pcd_bim = data_load(str(bim_path))

    progress("第2/4步 环境点云及缺失点云剔除", 2, 4)
    pcd_bim_down = voxel_downsample(pcd_bim, QA_BIM_DOWNSAMPLE_VOXEL)
    pcd_scene_clean = find_r(pcd_bim_down, pcd_scene, r=distance * 10)
    check_pt = find_k(pcd_scene_clean, pcd_bim, k=1)

    progress(f"第3/4步 偏差计算（{method}）", 3, 4)
    if method == "Point2Point":
        error = Error_caculate_Point2Point(check_pt, pcd_scene_clean, k=1)
    else:
        error = Error_caculate_Point2Plane(check_pt, pcd_scene_clean, r=distance)

    progress("第4/4步 偏差统计并生成报告", 4, 4)

    # 报告阶段从这里开始计时；上游点云读取、筛选和偏差计算已完成。
    report_progress("渲染输入点云图")
    figures.draw1(cache_dir / "fig1a.jpg", pcd_scene, 1, "red")
    figures.draw1(cache_dir / "fig1b.jpg", pcd_bim, 1, "blue")
    figures.draw2(cache_dir / "fig2.jpg", pcd_scene, pcd_bim, 1, 1, "red", "blue")

    report_progress("渲染环境/检测点图")
    figures.draw1(cache_dir / "fig3.jpg", pcd_scene_clean, 1, "red")
    figures.draw1(cache_dir / "fig4.jpg", check_pt, 1, "blue")

    report_progress("渲染偏差云图")
    figures.draw_error2(cache_dir / "fig5.jpg", check_pt, error * 1000, 2, ratio_value)

    error_sorted = sorted(error * 1000, reverse=True)
    line_number = int(len(error_sorted) * ratio_value)
    line = float(error_sorted[line_number])

    report_progress("导出偏差直方图（Plotly/Kaleido）")
    figure = figures.show_clum(error_sorted, step=1, ratio=ratio_value, cut_line=line, IS=4)
    figure.write_image(cache_dir / "Error_Analysis.jpg", format="png", scale=2)

    ui_step, ui_tick_stride = figures.ui_histogram_params(error_sorted)
    ui_figure = figures.show_clum(
        error_sorted, step=ui_step, ratio=ratio_value, cut_line=line, IS=ui_tick_stride
    )

    mean_val = float(np.mean(error_sorted))
    max_val = float(np.max(error_sorted))
    summary = {
        "check_num": int(len(error_sorted)),
        "error_max_cut": float(f"{line:.2f}"),
        "error_max": float(f"{max_val:.2f}"),
        "error_mean": float(f"{mean_val:.2f}"),
        "method": method,
        "unit": unit,
        "distance": distance,
        "ratio": ratio_value,
        "input_point_counts": {"scan": int(len(pcd_scene)), "bim": int(len(pcd_bim))},
        "figure": json.loads(figure.to_json()),
        "ui_figure": json.loads(ui_figure.to_json()),
    }
    basic_information = {
        "PCD_name": str(name),
        "SCENE_path": str(scene_path),
        "BIM_path": str(bim_path),
        "unit": str(unit),
        "method": str(method),
        "distance": float(distance),
        "ratio": float(ratio_value),
        "len_pcd_scene": int(len(pcd_scene)),
        "len_pcd_bim": int(len(pcd_bim)),
        "check_num": int(len(error_sorted)),
        "error_max_cut": float(f"{line:.2f}"),
        "error_max": float(f"{max_val:.2f}"),
        "error_mean": float(f"{mean_val:.2f}"),
    }

    report_progress("编译 PDF（latexmk/xelatex）")
    pdf.QA_Report(str(cache_dir), str(output_dir), basic_information)

    t = time.localtime()
    report_name = f"{name}几何质量评估报告{t[0]}{t[1]}{t[2]}.pdf"
    error_cloud = cache_dir / "error_cloud.npy"
    np.save(error_cloud, np.column_stack([check_pt, error]))
    return ToolResult(
        output_path=output_dir / report_name,
        display_name=report_name,
        summary=summary,
        internal_outputs={"error_cloud": error_cloud},
    )
