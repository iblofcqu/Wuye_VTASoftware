---
type: workflow-guide
title: 尺寸质量评估工作流
description: 从四项前置确认开始，说明尺寸质量评估如何读取点云、剔除环境与缺失区、计算 Point2Point/Point2Plane 偏差、统计并生成报告。
tags: [workflow, quality-assessment, deviation, streamlit]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:28:45.133Z
sources:
  - id: openwiki-source-3148fb605fdcb33f17c0cba5
    resource: repo://base_software/functions/knn.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
generated: { by: "codex", at: "2026-09-28T07:28:45.133Z" }
---

# 尺寸质量评估工作流

## 进入条件

用户必须先勾选四项确认：已获得离散点云、已完成（或明确忽略）下采样、扫描与离散点云单位一致、两侧点云已经匹配。四项全部满足后才显示数据选择和参数区；否则页面只提示当前数据不满足检测条件。

页面随后要求选择：

- 扫描点云：保存到 `QA_pcd.txt`。
- BIM/离散点云：保存到 `QA_BIM.txt`。
- 报告输出目录：保存到 `QA_Report.txt`。
- 点云单位：`m`、`dm`、`cm` 或 `mm`。
- 偏差方法：`Point2Point` 或 `Point2Plane`。
- 平面邻域大小 `distance`：默认 `0.01`。
- 需剔除的比例 `ratio`：默认 `0.05`。

这些值在 Streamlit 重跑时从界面重新生成，点击“计算偏差并生成报告”后从文本缓存读取实际文件路径。

## 第 1/4 步：读取和预览

页面从扫描点云路径推导 `PCD_name`，然后：

- 读取扫描点云，保存 `fig1a.jpg`。
- 读取 BIM 点云，保存 `fig1b.jpg`。
- 生成两者叠加的三维预览，并保存 `fig2.jpg`。

当前读取函数只对 `.xls`、`.xyz`、`.asc` 和 `.txt` 给出分支；其他扩展名不会在函数内返回明确的“不支持”错误，而可能在页面后续使用变量时失败。

## 第 2/4 步：环境与缺失区筛选

扫描环境剔除使用两层 KDTree 检索：

1. 先把 BIM 点云以 `0.1` 的固定体素尺寸下采样。
2. `find_r(pcd_bim_down, pcd_scene, r=distance * 10)` 对每个 BIM 下采样点在其扫描点云邻域中找点；只有半径内至少 11 个邻居的查询点才参与，最终把所有命中邻居的索引取并集，得到 `pcd_scene_clean`。
3. `find_k(pcd_scene_clean, pcd_bim, k=1)` 从 BIM 点云中找出与清洁扫描点云一一对应的最近点，并去重为 `check_pt`。

`distance` 的界面标签说明它只对 Point2Plane 有效，但环境剔除始终使用 `distance * 10`，所以选择 Point2Point 时该参数仍会改变检测点集合。BIM 下采样的 `0.1` 也没有单位换算或界面开关，实际含义取决于选中单位。

## 第 3/4 步：计算偏差

- `Point2Point`：对每个 `check_pt` 在 `pcd_scene_clean` 中取最近扫描点，距离作为偏差。
- `Point2Plane`：先找最近扫描点，再以 `distance` 为半径找邻域点并拟合局部平面，返回检测点到平面的距离。

若 Point2Plane 的邻域少于 3 个点，偏差被写成 `0`，不会从结果中排除，也不会报告该点无法计算。随后页面把偏差乘 1000，统一按 mm 进入三维显示、统计图和报告。

## 第 4/4 步：剔除线、统计与报告

页面将 mm 偏差降序排列，并以 `line_number = int(len(error_sorted) * ratio)` 取排序后的一个值作为剔除线。直方图保留全部检测点，只用红色虚线标识剔除位置；彩色偏差云图会把剔除线之前的最大偏差点显示为 0。

页面展示并写入报告的指标包括检测点数、剔除比例后的最大偏差、原始最大偏差和平均偏差。报告字典还包含：

- 扫描点云和 BIM 路径。
- `PCD_name`、单位、方法和平面邻域参数。
- 两侧原始点云点数。
- 检测点数及三项偏差统计。

最后调用 `QA_Report(cache_path, output_path, basic_information)` 生成中文 PDF，并用“打开输出文件夹”按钮读取 `QA_Report.txt`。

## 失败边界

- `distance`、`ratio` 的主要界面转换是直接 `float(...)`，没有范围校验或用户可读错误。
- `ratio` 为 1 时剔除线索引越界；负数比例会按 Python 负索引选取误差线。
- 空点云、`find_r` 没有任何命中点、Point2Plane 邻域过少以及报告图片缺失都缺少统一的领域错误处理，失败会表现为 NumPy/KDTree/Open3D 或文件系统异常。
- 核心计算链没有事务或回滚；某一步失败后，缓存中可能保留本轮早先已经覆盖的图片和路径。
