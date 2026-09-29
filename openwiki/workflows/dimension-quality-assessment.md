---
type: workflow-guide
title: 尺寸质量评估 B/S 工作流
description: 从四个前置确认到扫描/BIM 点云选择、后台四步计算、Point2Point/Point2Plane 偏差、受限浏览器直方图、报告超时和 PDF 报告的完整 B/S 链路。
tags: [workflow, quality-assessment, deviation, point2plane, report]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T08:08:46.977Z
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
  - id: openwiki-source-b3865b441eaafc9ac8594650
    resource: repo://frontend/src/components/DeviationHistogram.vue
  - id: openwiki-source-c0d31886011163a6c93bffe9
    resource: repo://frontend/src/utils/qa.ts
  - id: openwiki-source-d5099a190ac06d937fadf92d
    resource: repo://frontend/src/views/quality/QualityAssessView.vue
generated: { by: "codex", at: "2026-09-29T08:08:46.977Z" }
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

邻域少于 3 个点、平面近似共线/退化、法向量无效或误差非有限时，Point2Plane 把该点偏差记为 0；正常平面仍使用 SVD 拟合和质心投影。

### 4. 偏差统计并生成报告

- 偏差乘以 1000 统一按 mm 统计。
- 按降序排序，剔除线取索引 `int(len(errors) × ratio)` 的值。
- 偏差云图把最大 `ratio` 比例的点显示为 0，但保留在点集中。
- 报告 PDF 使用的 Plotly 直方图按 1 mm 区间统计并标注剔除线；浏览器另生成受限 `ui_figure`，最多 256 个柱和 20 个刻度。
- 统计四项指标：检测点数、剔除后最大值、最大值、平均值。
- 生成 `error_cloud.npy`，供任务偏差云预览接口使用。
- 报告阶段由 supervisor 子进程执行，默认 300 秒超时；正常完成才调用 PyLaTeX 生成 PDF 并登记为 `kind=report` 的 artifact。

## 前端结果展示

当任务状态为 `succeeded` 时，页面显示：

- `DeviationHistogram` 与四项统计指标；框架优先使用 `summary.ui_figure`，并在 Plotly 边界把 Vue 响应式 figure 克隆为普通 JSON 对象。
- `PointCloudViewer`，通过 `GET /api/jobs/{job_id}/preview` 加载偏差云 WYPV。
- `ReportCard`，从任务 artifact 中提取 `kind=report` 的 PDF 并提供下载。

前端展示与 PDF 报告使用同一次任务的结果摘要/图片，不再像 base_software 那样依赖共享 `cache` 目录中的固定文件。

## Point2Plane 退化处理

`fit_plane()` 对去中心化邻域做 SVD，并同时返回平面参数和拟合点质心；当最小奇异值相对第一奇异值过小时，点近似共线/平面退化，函数返回 `None`。`Error_caculate_Point2Plane()` 使用质心作为平面上已知点做投影，避免旧实现对法向量 z 分量直接除法。

因此，邻域不足、退化平面、无效法向量或非有限误差会显式回退为 0，而不是产生 `NaN`/`Inf` 并让后续直方图在 `np.arange` 处失败。正常平面结果仍与基线样本对比。

## 失败与边界

- 非法单位、方法、非正 `distance` 和不在 `[0,1)` 的 `ratio` 会在服务层显式抛错。
- 点云为空、`find_r` 找不到满足条件的邻域等底层异常会进入任务失败状态。
- 失败任务不产生 report artifact；页面在 `JobProgress` 中展示错误文本。
- 预览接口只对已成功任务开放；偏差云缺失或格式错误返回 422。
- 报告阶段超过 `WUYE_REPORT_TIMEOUT_SECONDS` 时任务失败、不登记 PDF，并报告最后阶段。
- 当前没有自动判断配准质量；Point2Plane 已对退化平面做 0 值回退。

## 相关页面

- [异步任务执行与进度](async-job-execution.md)
- [点云处理算法与基线约束](../algorithms/point-cloud-processing.md)
- [质量报告生成与工具链](../reporting/quality-report-generation.md)
- [点云预览管线](../architecture/point-cloud-preview-pipeline.md)
- [快速开始](../quickstart.md)
