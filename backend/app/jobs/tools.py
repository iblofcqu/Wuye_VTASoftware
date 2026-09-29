"""工具注册表：把服务层封装为进程池可执行的 worker。"""

from app.services import preprocessing, quality, registration

INPUT_SPECS = {
    "mesh-discretize": ("input",),
    "scale": ("input",),
    "downsample-voxel": ("input",),
    "downsample-uniform": ("input",),
    "register-fpfh": ("moving", "fixed"),
    "register-icp": ("moving", "fixed"),
    "quality-assess": ("scan", "bim"),
}


def _payload(result, *, kind: str) -> dict:
    return {
        "outputs": [
            {"path": str(result.output_path), "display_name": result.display_name, "kind": kind}
        ],
        "summary": result.summary,
        "internal_outputs": {key: str(value) for key, value in result.internal_outputs.items()},
    }


def run_mesh_discretize(params, inputs, work_dir, progress):
    result = preprocessing.grid_discretize(
        inputs["input"], work_dir, distance_points=params.get("distance_points"), progress=progress
    )
    return _payload(result, kind="pointcloud")


def run_scale(params, inputs, work_dir, progress):
    result = preprocessing.scale(
        inputs["input"],
        work_dir,
        origin_unit=params.get("origin_unit"),
        target_unit=params.get("target_unit"),
        progress=progress,
    )
    return _payload(result, kind="pointcloud")


def run_downsample_voxel(params, inputs, work_dir, progress):
    result = preprocessing.downsample_voxel(
        inputs["input"], work_dir, voxel_size=params.get("voxel_size"), progress=progress
    )
    return _payload(result, kind="pointcloud")


def run_downsample_uniform(params, inputs, work_dir, progress):
    result = preprocessing.downsample_uniform(
        inputs["input"], work_dir, every_k=params.get("every_k"), progress=progress
    )
    return _payload(result, kind="pointcloud")


def run_register_fpfh(params, inputs, work_dir, progress):
    result = registration.register_fpfh(
        inputs["moving"],
        inputs["fixed"],
        work_dir,
        voxel_size=params.get("voxel_size"),
        progress=progress,
    )
    return _payload(result, kind="pointcloud")


def run_register_icp(params, inputs, work_dir, progress):
    thresholds = params.get("thresholds", registration.ICP_DEFAULT_THRESHOLDS)
    result = registration.register_icp(
        inputs["moving"],
        inputs["fixed"],
        work_dir,
        thresholds=thresholds,
        progress=progress,
    )
    return _payload(result, kind="pointcloud")


def run_quality_assess(params, inputs, work_dir, progress):
    result = quality.assess(
        inputs["scan"],
        inputs["bim"],
        work_dir,
        work_dir / "cache",
        unit=params.get("unit"),
        method=params.get("method"),
        distance=params.get("distance"),
        ratio=params.get("ratio"),
        progress=progress,
    )
    return _payload(result, kind="report")


TOOL_REGISTRY = {
    "mesh-discretize": run_mesh_discretize,
    "scale": run_scale,
    "downsample-voxel": run_downsample_voxel,
    "downsample-uniform": run_downsample_uniform,
    "register-fpfh": run_register_fpfh,
    "register-icp": run_register_icp,
    "quality-assess": run_quality_assess,
}
