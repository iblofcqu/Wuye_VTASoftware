---
type: algorithm-reference
title: 点云处理算法与基线约束
description: 说明 backend/app/algos 中网格离散、下采样、FPFH/ICP 配准、KDTree 偏差度量和平面拟合的输入输出、参数语义、与 base_software 的迁移一致性，以及 Point2Plane 退化平面的当前处理。
tags: [point-cloud, algorithms, registration, sampling, parity]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T08:08:46.977Z
sources:
  - id: openwiki-source-c578b2dc2526160d08abde24
    resource: repo://backend/app/algos/knn.py
  - id: openwiki-source-3c9f6dc73f712ad038ac5255
    resource: repo://backend/app/algos/load_data.py
  - id: openwiki-source-b2155c0405a34f9e4fd6857d
    resource: repo://backend/app/services/preprocessing.py
  - id: openwiki-source-fdf91f260fb2d57c38f672b5
    resource: repo://backend/app/services/registration.py
  - id: openwiki-source-a4609782da505aa28ee1da22
    resource: repo://backend/tests/test_golden_parity.py
  - id: openwiki-source-be678524275ac5170073c381
    resource: repo://base_software/functions/down_samples.py
  - id: openwiki-source-c430c92bafb6ac714f9dd000
    resource: repo://base_software/functions/FPFH.py
  - id: openwiki-source-3148fb605fdcb33f17c0cba5
    resource: repo://base_software/functions/knn.py
  - id: openwiki-source-9b9d978afb5e2b72c2de72f8
    resource: repo://base_software/functions/Poisson_Disk_Sampling.py
  - id: openwiki-source-89338bb119d2b3d5509994ce
    resource: repo://base_software/functions/Registration.py
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
generated: { by: "codex", at: "2026-09-29T08:08:46.977Z" }
---

# 点云处理算法与基线约束

## 实现位置与迁移边界

`base_software/functions/` 是原始 Streamlit 实现，也是行为基线；`backend/app/algos/` 保存迁移后的算法模块。当前 B/S 服务层从后者导入算法，迁移约束是让正常输入尽量保持原实现的数值结果和输出命名。Point2Plane 的退化平面处理后来作为独立缺陷修复：正常平面仍按 SVD 拟合，近共线/退化邻域不再进入旧的零分量除法路径。

`backend/app/services/` 在算法外包了一层参数校验、输出命名和进度回调。服务层对网格离散、缩放、下采样、粗配准和精配准的输入参数做显式检查，算法模块本身大多仍假设调用者提供正确形状的 NumPy 点数组。

## 共同输入输出约定

- 点云在算法之间以 NumPy 数组传递，通常使用前三列 `x`、`y`、`z`。
- 当前服务通过 `data_load()` 读取点云；该函数使用 Open3D 的 `format='xyz'` 进入内存。模块中还保留 `data_read()` 的扩展名分支，用于历史代码中 `.xls`、`.xyz`、`.asc`、`.txt` 的 pandas 读取路径。
- 单位缩放使用 `{m: 1, dm: 0.1, cm: 0.01, mm: 0.001}`，计算“原单位系数 / 目标单位系数”后乘坐标，不改变坐标轴或做非线性变换。
- 输出文件统一由服务层写入工作目录；文件命名规则属于工作流契约，而不是算法返回值的一部分。

## 网格离散与下采样

`Mesh_to_PCD()` 先读取三角网格、计算顶点法向量和表面面积，再按 `点数 = 表面积 / 点间距²` 估算 `sample_points_poisson_disk()` 的目标点数，最后返回采样点的 NumPy 坐标。

Poisson-disk 采样本身带有随机性。迁移回归不要求逐点一致，而是核对点数、质心、包围盒和平均最近邻间距；点数由面积和间距决定，必须与基线一致。

下采样模块提供：

- `voxel_downsample()`：调用 Open3D 体素下采样。
- `uniform_downsample()`：按 `every_k_points` 间隔均匀取样。
- `farthest_point_down_sample()`：按目标点数执行最远点采样。
- `random_down_sample()`：按比例随机保留点。

当前 B/S 工具主要使用体素和均匀两种；随机下采样没有显式随机种子，不能把重复运行的输出视为确定的。

## FPFH 粗配准

`FPFH_Registration()` 先按固定矩阵交换源点云的坐标轴，再对源、目标点云分别执行同一套预处理：

- 体素下采样尺寸由调用者传入。
- 法向量搜索半径为 `2 × voxel_size`，最多使用 30 个邻点。
- FPFH 特征搜索半径为 `5 × voxel_size`，最多使用 100 个邻点。
- RANSAC 距离阈值为 `1.5 × voxel_size`，使用 3 个采样点、边长与距离检查器，以及迭代/置信度参数 `(100000, 1)`。
- 最终把 RANSAC 得到的变换应用到源点云并返回变换后的坐标。

由于 RANSAC 和特征匹配包含随机性，重复运行可能落到不同局部最优。回归测试首先验证三个 FPFH 相关函数与基线源码逐字一致，再用“配准后到固定点云的平均最近邻距离”作为质量契约，不把随机波动伪装成逐次确定结果。

## ICP 精配准

`Open3d_ICP()` 使用单位矩阵作为初始变换，先估计源、目标法向量，再调用点到平面 ICP。需要注意：

- 目标点云由 `target_data[2:]` 构造，因此目标前两个点不会参与本次精配准。
- 法向量估计使用半径 `2`、最多 `8` 个邻点。
- B/S 精配准服务按 `0.05`、`0.03`、`0.005` 三个默认阈值依次调用三次 `Open3d_ICP()`，每一次都把上一次结果作为下一次源点云。
- `Registration_rough_ICP()` 还提供“球心配准 + 三次 ICP + 坐标去重”的组合路径，但当前 B/S 精配准服务没有调用它。

算法完成不代表配准必然正确。当前实现的输出没有自动质量断言；页面侧仍要求使用者查看预览并决定是否重跑或更换输入。

## KDTree 偏差与平面拟合

质量评估的 KDTree 链路如下：

1. `find_r(data, original, r)` 对目标点云建立 KDTree，只保留半径邻点数大于 10 的查询点，再对所有命中邻点索引取并集。
2. `find_k(data, original, k)` 对每个查询点取 `k` 个最近邻索引，去重后返回对应原始点。
3. `Error_caculate_Point2Point()` 返回检测点到参考点云的最近点距离。
4. `Error_caculate_Point2Plane()` 先找最近点，再在半径 `r` 的邻域内用 SVD 拟合平面，最后计算检测点到拟合平面的法向距离。

平面拟合 `fit_plane()` 对去中心化点云做 SVD：

- 取最小奇异值对应的右奇异向量作为法向量；
- 同时返回平面参数 `[A, B, C, D]` 和参与拟合点的质心；
- 当 `S[2]` 相对 `S[0]` 过小、点近似共线或平面退化时返回 `None`。

`Error_caculate_Point2Plane()` 随后使用质心作为平面上的已知点做投影，避免旧实现对 `plane_model[2]` 直接做除法。当前边界行为是：

- 邻域少于 3 个点、平面退化为 `None`、法向量无效或误差非有限时，该点偏差记为 `0`；
- 正常平面仍使用局部 SVD 拟合和点到平面距离；
- 不再因为局部平面的 z 分量为 0 而产生 `inf`/`NaN`，也不会因此让后续直方图统计失败。

## 基线验证提供了什么

`test_golden_parity.py` 覆盖了几类不同的验证强度：

- 点云读取、单位缩放和体素/均匀下采样：与基线逐点完全一致。
- Poisson-disk 网格离散：点数必须一致，位置允许与采样间距相关的显式容差。
- FPFH：先验证源码逐字一致，再验证单次运行质量显著优于未配准基线。
- 已知边界：Point2Plane 邻域不足记 0、`find_r` 空结果抛错等行为按原样保留并断言；近似共线的退化平面现在走显式的 0 值回退路径。

因此，算法页上的“与原实现一致”主要表示行为契约和验证容差，而不是声称所有随机算法在每次运行中产生相同坐标。

## 相关页面

- [点云预处理 B/S 工作流](../workflows/point-cloud-preprocessing.md)
- [尺寸质量评估 B/S 工作流](../workflows/dimension-quality-assessment.md)
- [测试、Golden 基线与端到端验收](../development/testing-and-golden-parity.md)
- [点云预览管线](../architecture/point-cloud-preview-pipeline.md)
