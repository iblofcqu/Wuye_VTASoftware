---
type: algorithm-reference
title: 点云处理算法
description: 说明项目内采样、网格离散、FPFH/RANSAC、ICP、KDTree 偏差度量与平面拟合算法的输入输出、参数语义和当前实现限制。
tags: [point-cloud, algorithms, registration, sampling]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:28:45.133Z
sources:
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
generated: { by: "codex", at: "2026-09-28T07:28:45.133Z" }
---

# 点云处理算法

## 统一输入输出约定

大多数算法模块接收 NumPy 点数组并以 NumPy 数组返回结果，坐标统一使用前三列 `xyz`。下采样、FPFH、ICP 和 KDTree 相关函数都遵循这一约定，因此页面层可以直接串联不同函数，而不需要额外转换对象。

## 网格离散与下采样

- 网格离散先读取三角网格、计算表面积，再按 `点数 = 表面积 / 点间距²` 估算采样数量，最后调用 Open3D 的 Poisson-disk 采样。
- 体素下采样用体素内点集的重心代表该体素；均匀下采样每隔 `every_k_points` 取一个点；最远点采样直接指定最终点数；随机下采样按比例保留点。
- 这些函数都不修改传入数组，而是返回新的 NumPy 数组。页面中的尺寸缩放则使用 `{m: 1, dm: 0.1, cm: 0.01, mm: 0.001}`，以“原单位系数 / 目标单位系数”乘坐标，完成线性单位换算。

## FPFH 粗配准

`FPFH_Registration` 先按固定矩阵交换坐标轴，然后对源点云和目标点云执行同一套 FPFH 预处理：

- 体素下采样尺寸由调用者提供。
- 法向量搜索半径为 `2 × voxel_size`，最多使用 30 个邻点。
- FPFH 特征搜索半径为 `5 × voxel_size`，最多使用 100 个邻点。
- RANSAC 内点距离阈值为 `1.5 × voxel_size`，置信度与迭代参数分别为 `100000` 和 `1`，并使用边长与距离检查器筛选对应关系。
- 最终把 RANSAC 得到的变换应用到源点云，返回变换后的坐标。

源码中的参数比例内嵌在函数里，只把 `voxel_size` 暴露给调用方；界面也不会验证该值是否为正数。

## ICP 精配准

项目提供两条 ICP 路径：

1. `Open3d_ICP` 使用点到平面误差、单位矩阵作为初始变换，并在计算前为源、目标估计法向量。其目标点云实际从 `target_data[2:]` 开始，也就是会跳过目标点云的前两个点；这是当前实现的可见行为。
2. `ICP2` 允许用一个抽样点云求变换，再把同一变换同时应用到抽样点和完整源点云，适合避免用全量点云反复计算 ICP。

页面上的“精配准”连续调用三次 `Open3d_ICP`，默认阈值依次为 `0.05`、`0.03`、`0.005` 米。`Registration_rough_ICP` 还组合了球心粗配准与三次 ICP，并会对合并结果按坐标去重，但该组合函数没有出现在当前两个 Streamlit 页面的调用链中。

## 邻域检索与偏差度量

- `find_r` 以目标点云建立 KDTree，仅保留半径内邻点数大于 10 的查询点，再对所有邻点索引取并集。
- `find_k` 对每个查询点取 `k` 个最近邻并合并唯一索引。
- `Error_caculate_Point2Point` 返回每个检测点到扫描点云的最近距离。
- `Error_caculate_Point2Plane` 先找最近点，再在该点半径邻域内拟合平面，最后返回检测点到拟合平面的法向距离。

`fit_plane` 用 SVD 的最小奇异值对应向量作为平面法向量。Point2Plane 在半径内少于 3 个点时会直接写入偏差 `0`，而不是跳过、报错或记录无法计算；这会把“邻域不足”与“零偏差”混在同一结果中，是本模块需要重点关注的实现限制。

## 失效边界

- 空查询集合、找不到满足 `find_r` 条件的邻域，以及参数类型或范围不合法时，部分函数会在 `np.hstack`、类型转换或 Open3D 调用处直接抛错。
- 随机下采样没有显式随机种子，相同输入不保证得到相同输出。
- Point2Plane 用 `plane_model[3] / plane_model[2]` 构造平面点；当拟合平面的法向量 z 分量为零时存在除零风险。
- FPFH、RANSAC 和 ICP 的收敛及结果质量没有被现有代码校验；执行完成不等于配准正确，仍需人工查看页面预览并决定是否重跑。
