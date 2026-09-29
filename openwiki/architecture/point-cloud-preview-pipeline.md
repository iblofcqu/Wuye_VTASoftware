---
type: architecture-guide
title: 点云预览管线
description: 说明服务端点云轻量化与 WYPV 二进制编码、会话内缓存和预览 API，以及前端解析、vtk.js 渲染、配色和 WebGL2 不可用时的失败边界。
tags: [preview, point-cloud, wypv, vtk-js, webgl2]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-31623113e3a04b58893f3218
    resource: repo://backend/app/api/preview.py
  - id: openwiki-source-7c751c107cacf372c92785f6
    resource: repo://backend/app/core/preview.py
  - id: openwiki-source-ed437f83ef97dbc72fd4755f
    resource: repo://backend/tests/test_preview_api.py
  - id: openwiki-source-af5f6ec3d9894e8c7ee84c9c
    resource: repo://backend/tests/test_preview_core.py
  - id: openwiki-source-62c1462ca643d265eb668123
    resource: repo://frontend/src/components/PointCloudViewer.vue
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 点云预览管线

## 目标与数据边界

预览链路的目标是让浏览器只接收轻量化的展示数据，不改变任何计算任务使用的全量产物。服务端先在当前会话目录中生成预览缓存，前端再通过 HTTP 获取并解析 WYPV 二进制；全量点云文件仍通过产物下载接口获取，算法始终使用原产物。

## 服务端编码与轻量化

`backend/app/core/preview.py` 定义 WYPV 格式：

```text
MAGIC "WYPV" (4B)
+ version (1B)
+ header_len (4B, little-endian)
+ JSON header
+ positions (Float32, N×3)
+ optional scalars (Float32, N)
```

JSON 头包含 `count`、`source_count`、`decimated`、`fields`、名称和可选标量范围/单位/色带。`encode_preview()` 接受 `N×3` 点云和可选标量，首先按 `WYPV` 头部记录源点数，然后调用 `decimate_points()`：

- 点数不超过 `max_points` 时直接返回全部点。
- 超过上限时用固定种子 `0` 的 NumPy `default_rng` 做确定性随机抽样。
- 抽样索引同时用于对齐标量，保证位置与标量一一对应。
- 默认上限来自 `WUYE_PREVIEW_MAX_POINTS`，当前为 1,000,000。

`artifact_preview()` 负责产物预览：缓存路径为 `<session>/previews/artifact-<artifact_id>.bin`，命中缓存时直接返回；未命中时读取产物文本点云、编码并原子写入缓存。该函数支持 `.xyz`、`.asc`、`.txt`（NumPy）和 `.xls`（pandas）；其他格式直接以“暂不支持预览”失败。预览失败不会修改或移动原产物，因此下载和后续计算仍可用。

## 偏差云预览

质量评估成功后会生成一个内部 `error_cloud.npy`。`job_error_preview()` 读取该文件的前三列坐标和第四列标量：

- 标量乘以 `1000`，按 mm 进入预览。
- 从任务参数读取 `ratio`，把误差最大的 `int(N × ratio)` 个点标量置零。
- 编码为带 `scalar`、`scalar_unit=mm`、`colormap=seismic` 和 `zeroed_ratio` 的 WYPV。
- 缓存到 `<session>/previews/job-<job_id>.bin`。

这与报告图片中的“剔除后置零”语义一致，但预览只用于显示，不改变评估统计或下载产物。

## 预览 API

`backend/app/api/preview.py` 提供两个只读接口：

| 接口 | 行为 | 失败边界 |
| --- | --- | --- |
| `GET /api/artifacts/{artifact_id}/preview` | 生成或读取点云产物预览 | 非点云 400；路径非法或文件缺失 422 |
| `GET /api/jobs/{job_id}/preview` | 生成或读取质量评估偏差云预览 | 任务不存在 404；未成功 409；无偏差云 422 |

两个接口都通过当前会话 `session_id` 解析产物或任务，响应类型为 `application/octet-stream`。接口不返回服务器绝对路径，预览数据也不能跨会话读取。

## 前端解析

`frontend/src/utils/wypv.ts` 按小端格式解析 ArrayBuffer：校验 `WYPV` magic、版本、头部长度和坐标/标量字节长度；成功后返回 `{ header, positions, scalars? }`。如果 magic 错误、头部截断、版本不一致或坐标/标量不足，会抛出可直接展示的错误。

`frontend/src/components/PointCloudViewer.vue` 接收一组 `ViewerLayer`：

1. 对每个 layer 用同源 fetch 获取预览。
2. 解析 WYPV，把 positions 设置为 `vtkPolyData` 点数组。
3. 每个点构造一个 vertex cell，并用 `vtkMapper`/`vtkActor` 加入 renderer。
4. 无标量时使用 layer 指定颜色；有标量时使用 `seismicStops()` 构造 vtk.js 颜色传递函数。
5. 完成加载后重置相机并渲染，组件卸载时释放 actors、render window 和 ResizeObserver。

`parseColor()` 支持 red/blue/grey/gray/black/white 和 `#rrggbb`；默认回退红色。seismic 色带从深蓝经白到红/暗红，与质量评估偏差图的视觉语义对应。

## WebGL2 失败边界

vtk.js 的三维渲染依赖 WebGL2。`PointCloudViewer` 在创建 render window 前用临时 canvas 检查 `getContext('webgl2')`；初始化过程也被 try/catch 包裹。

- 无法创建 WebGL2 时，组件显示明确错误，提示检查 `chrome://gpu`、WebGL2 和硬件加速；不会继续调用 `loadLayers()`，因此不会发起点云预览请求。
- renderer 初始化抛错时同样转为可见错误，而不是留下空白画布或未捕获异常。
- 在无 WebGL2 的虚拟机或受 GPU 黑名单影响的 Chrome 中，预览不可用，但产物下载和后续计算不受影响。

这与基线 PyVista 预览不同：原实现依赖服务端桌面/离屏渲染，B/S 版本把交互预览交给浏览器 WebGL2，因此运行环境能力会直接影响预览可见性。

## 验证边界

- 后端测试验证 WYPV 头、默认点数上限、缓存命中、标量在抽样后仍与坐标对齐，以及偏差云置零语义。
- API 测试验证产物预览成功、运行中任务不可预览、损坏或缺失产物显式失败，同时下载不受影响。
- 前端单测验证 WYPV 坐标/标量解析、非法数据拒绝和命名色/seismic 端点；三维渲染本身依赖浏览器 WebGL2，未在单元测试中模拟完整 GPU 环境。

## 相关页面

- [点云处理算法与基线约束](../algorithms/point-cloud-processing.md)
- [浏览器—服务端架构](browser-server-architecture.md)
- [点云预处理 B/S 工作流](../workflows/point-cloud-preprocessing.md)
- [尺寸质量评估 B/S 工作流](../workflows/dimension-quality-assessment.md)
