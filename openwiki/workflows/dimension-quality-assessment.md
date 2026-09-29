---
type: workflow-guide
title: 尺寸质量评估 B/S 工作流
description: 从四个前置确认到扫描/BIM 点云选择、后台四步计算、Point2Point/Point2Plane 偏差、统计指标、偏差云预览和 PDF 报告的完整 B/S 链路。
tags: [workflow, quality-assessment, deviation, point2plane, report]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-c578b2dc2526160d08abde24
    resource: repo://backend/app/algos/knn.py
  - id: openwiki-source-31623113e3a04b58893f3218
    resource: repo://backend/app/api/preview.py
  - id: openwiki-source-5cd8a5b32eb393895819dfdc
    resource: repo://backend/app/jobs/runner.py
  - id: openwiki-source-115bc96dd839c419e53a5004
    resource: repo://backend/app/report/figures.py
  - id: openwiki-source-29449cdcdd8456fbc5b9b089
    resource: repo://backend/app/services/quality.py
  - id: openwiki-source-3148fb605fdcb33f17c0cba5
    resource: repo://base_software/functions/knn.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
  - id: openwiki-source-d5099a190ac06d937fadf92d
    resource: repo://frontend/src/views/quality/QualityAssessView.vue
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 尺寸质量评估 B/S 工作流

## 页面入口与前置确认

页面路由为 `/quality/assess`。用户必须先勾选四项确认：

- 已获取离散点云；
- 已完成或明确忽略下采样；
- 已检查离散点云与扫描点云单位一致；
- 已完成扫描点云与离散点云的匹配。

四项全部满足后，页面才显示输入与参数区；否则显示空状态，不开放任务提交。

## 输入与参数

页面通过 `ArtifactPicker` 从当前会话选择扫描点云和 BIM 点云，也允许上传新文件。可选参数为：

| 参数 | 当前默认 | 语义 |
| --- | --- | --- |
| `unit` | `m` | 点云单位，可取 m/dm/cm/mm |
| `method` | `Point2Point` | 偏差计算方法 |
| `distance` | `0.01` | Point2Plane 的平面邻域大小，同时参与环境点剔除 |
| `ratio` | `0.05` | 剔除偏差最大的点占比 |

前端把输入和参数提交为 `quality-assess` 异步任务；它只发送 artifact id，不发送服务器路径。

## 后台四步

`backend/app/services/quality.py` 按四个阶段执行：

### 1. 文件读取

读取扫描点云和 BIM 点云，生成 `fig1a.jpg`、`fig1b.jpg` 和两者叠加的 `fig2.jpg`。输入点云可以是会话产物或刚上传的 artifact。

### 2. 环境点云与缺失点云剔除

- BIM 点云先按固定体素 `0.1` 下采样。
- 以 `distance × 10` 为半径，从扫描点云中筛选 BIM 附近的环境点，生成清洁扫描点云 `pcd_scene_clean`。
- 从 BIM 点云中为清洁扫描点寻找最近点，去重得到检测点 `check_pt`。

因此，即使选择 Point2Point，修改 `distance` 仍会改变检测点集合。

### 3. 偏差计算

- **Point2Point**：检测点到清洁扫描点云的最近距离。
- **Point2Plane**：先找最近扫描点，再在 `distance` 半径内拟合局部平面，计算检测点到平面的法向距离。

邻域少于 3 个点时，Point2Plane 按原实现把该点偏差记为 0。

### 4. 偏差统计并生成报告

- 偏差乘以 1000 统一按 mm 统计。
- 按降序排序，剔除线取索引 `int(len(errors) × ratio)` 的值。
- 偏差云图把最大 `ratio` 比例的点显示为 0，但保留在点集中。
- Plotly 直方图按 1 mm 区间统计并标注剔除线。
- 统计四项指标：检测点数、剔除后最大值、最大值、平均值。
- 生成 `error_cloud.npy`，供任务偏差云预览接口使用。
- 调用 PyLaTeX 报告模块生成 PDF，并登记为 `kind=report` 的 artifact。

## 前端结果展示

当任务状态为 `succeeded` 时，页面显示：

- `DeviationHistogram` 与四项统计指标，数据来自任务 `summary`。
- `PointCloudViewer`，通过 `GET /api/jobs/{job_id}/preview` 加载偏差云 WYPV。
- `ReportCard`，从任务 artifact 中提取 `kind=report` 的 PDF 并提供下载。

前端展示与 PDF 报告使用同一次任务的结果摘要/图片，不再像 base_software 那样依赖共享 `cache` 目录中的固定文件。

## 已知 Point2Plane 退化行为

当前 Point2Plane 实现把局部平面点写为：

```text
[0, 0, -(plane_model[3] / plane_model[2])]
```

当拟合平面的法向量 `z` 分量为 0（竖直/轴对齐平面或退化邻域）时，除法会产生 `inf`/`NaN`，进而使偏差数组包含非有限值。后续直方图统计在 `np.max` 得到 NaN 后可能触发：

```text
ValueError: arange: cannot compute length
```

这是一个已复现的基线与 B/S 共有算法边界，不是任务框架问题；当前迁移没有自动修复。遇到该数据/参数组合时，任务会失败且不会登记报告产物。

## 失败与边界

- 非法单位、方法、非正 `distance` 和不在 `[0,1)` 的 `ratio` 会在服务层显式抛错。
- 点云为空、`find_r` 找不到满足条件的邻域等底层异常会进入任务失败状态。
- 失败任务不产生 report artifact；页面在 `JobProgress` 中展示错误文本。
- 预览接口只对已成功任务开放；偏差云缺失或格式错误返回 422。
- 当前没有自动判断配准质量或 Point2Plane 数值稳定性的质量门禁。

## 相关页面

- [异步任务执行与进度](async-job-execution.md)
- [点云处理算法与基线约束](../algorithms/point-cloud-processing.md)
- [质量报告生成与工具链](../reporting/quality-report-generation.md)
- [点云预览管线](../architecture/point-cloud-preview-pipeline.md)
- [快速开始](../quickstart.md)
