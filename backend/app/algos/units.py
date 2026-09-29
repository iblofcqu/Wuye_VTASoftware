"""尺寸缩放的单位换算：语义与 base_software/pages/1_点云预处理.py 的尺寸缩放模块一致。"""

UNIT_TO_METER = {"m": 1, "dm": 0.1, "cm": 0.01, "mm": 0.001}


def scale_points(points, origin, target):
    """按基线页面的 Dictionary[origin] / Dictionary[target] 系数缩放点云。"""
    coefficient = float(UNIT_TO_METER[origin] / UNIT_TO_METER[target])
    return points * coefficient
