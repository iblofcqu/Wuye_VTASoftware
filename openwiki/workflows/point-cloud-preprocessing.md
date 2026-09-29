---
type: workflow-guide
title: 点云预处理 B/S 工作流
description: 说明浏览器中网格离散、尺寸缩放、体素/均匀下采样、FPFH 粗配准和三次 ICP 精配准的输入选择、任务提交、输出命名、预览与会话内交接。
tags: [workflow, preprocessing, registration, artifacts, browser-server]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-641ae98462ef0e5867e3c63c
    resource: repo://backend/app/core/sessions.py
  - id: openwiki-source-af8bc07dd356b94582111a05
    resource: repo://backend/app/core/uploads.py
  - id: openwiki-source-5cd8a5b32eb393895819dfdc
    resource: repo://backend/app/jobs/runner.py
  - id: openwiki-source-fecf2f8a5b5c8cf503ca5e77
    resource: repo://backend/app/jobs/tools.py
  - id: openwiki-source-b2155c0405a34f9e4fd6857d
    resource: repo://backend/app/services/preprocessing.py
  - id: openwiki-source-fdf91f260fb2d57c38f672b5
    resource: repo://backend/app/services/registration.py
  - id: openwiki-source-9b9d978afb5e2b72c2de72f8
    resource: repo://base_software/functions/Poisson_Disk_Sampling.py
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
  - id: openwiki-source-b4c959afbd45d736542ecd0d
    resource: repo://frontend/src/components/ArtifactPicker.vue
  - id: openwiki-source-77c413f182fc2eead5535edb
    resource: repo://frontend/src/router/index.ts
  - id: openwiki-source-0037485c266dfb010270ce6d
    resource: repo://frontend/src/views/preprocess/DiscretizeView.vue
  - id: openwiki-source-a9566f1024bc09f05db887ec
    resource: repo://frontend/src/views/preprocess/DownsampleView.vue
  - id: openwiki-source-ca64c3e18d3de19e870c8957
    resource: repo://frontend/src/views/preprocess/RegistrationView.vue
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 点云预处理 B/S 工作流

## 工具与路由

当前前端把预处理拆成独立页面：

| 工具 | 路由 | 任务工具 id |
| --- | --- | --- |
| 网格离散 | `/preprocess/discretize` | `mesh-discretize` |
| 尺寸缩放 | `/preprocess/scale` | `scale` |
| 下采样 | `/preprocess/downsample` | `downsample-voxel` / `downsample-uniform` |
| 配准 | `/preprocess/registration` | `register-fpfh` / `register-icp` |

每个页面通过 `ArtifactPicker` 选择当前会话中的 pointcloud/mesh artifact，也允许直接用 `FileUploader` 上传新文件。页面只提交 artifact id 和参数，任务 API 再从会话中解析内部文件路径。

## 共同交互流程

典型步骤是：

1. 选择或上传输入文件。
2. 填写参数并提交任务。
3. `JobProgress` 轮询任务状态和阶段进度。
4. 任务成功后，页面刷新 workspace 会话快照。
5. 结果进入 `artifacts` 列表，显示预览和下载链接，并可被后续步骤选择。

所有工具都使用异步任务，不在浏览器请求线程中执行点云算法。失败任务不会登记结果 artifact，错误文本显示在任务进度卡中。

## 网格离散

输入是 mesh artifact，参数是点云间距。服务调用 `Mesh_to_PCD()`，输出：

```text
<网格主名>.xyz
```

输出登记为 pointcloud artifact，可立即请求 WYPV 预览。点云间距会经过正数校验；非法值使任务失败而不是把非法字符串传给算法。

网格离散的主要采样调用是单个 Open3D 阻塞步骤，没有细粒度内部进度；页面的 `1/2`、`2/2` 只是服务层阶段标记，不是采样算法内部百分比。

## 尺寸缩放

输入是 pointcloud artifact，参数是原单位和目标单位。支持 `m`、`dm`、`cm`、`mm`，按：

```text
原单位系数 / 目标单位系数
```

乘坐标，输出：

```text
<原点云主名>_<目标单位>.xyz
```

服务层会拒绝未知单位。缩放输出重新登记为当前会话的 pointcloud artifact，因此可以继续送往下采样、配准或质量评估。

## 下采样

### 体素下采样

调用 `voxel_downsample(points, voxel_size)`，输出：

```text
<输入主名>_VD.xyz
```

体素尺寸必须为正数；服务层返回 summary 中的输入点数和输出点数，页面可用于快速检查采样程度。

### 均匀下采样

调用 `uniform_downsample(points, every_k)`，输出：

```text
<输入主名>_UD.xyz
```

采样间隔必须是正整数。该操作按 Open3D `every_k_points` 语义执行，输出同样登记为会话 artifact。

## FPFH 粗配准

粗配准需要待配准点云和固定点云。服务调用 `FPFH_Registration(moving, fixed, voxel_size)`，输出：

```text
<待配准点云主名>_FPFH.xyz
```

体素大小必须为正数。FPFH/RANSAC 是随机算法，页面不能把一次完成视为配准正确；用户需要查看移动点云与固定点云的叠加预览，并在效果不理想时调整体素大小重试。

成功产物进入会话 artifact 列表。`RegistrationView` 在粗配准任务成功后会把该 artifact 自动填入精配准的“待配准点云”，如果精配准固定点云尚未选择，还会沿用粗配准的固定点云；用户仍可手动改选其他产物。

## ICP 精配准

精配准默认阈值是：

```text
0.05、0.03、0.005
```

页面以数组形式提交三个阈值，服务层要求恰好三个正数。之后依次调用 `Open3d_ICP()` 三次，每次以上一次结果为源点云，最终输出：

```text
<待配准点云主名>_ICP.xyz
```

`Open3d_ICP` 使用点到平面 ICP，并有一个需要保留的基线行为：目标点云使用 `target_data[2:]`，目标前两个点不会参与本次精配准。服务不自动判断配准收敛质量。

## 会话内复用与预览

每个成功工具都会把输出登记为 artifact：

- 网格离散、缩放、下采样和配准结果都是 pointcloud；
- 结果可以下载，或在后续页面的 ArtifactPicker 中选择；
- 点云预览由服务端生成 WYPV，浏览器通过 `PointCloudViewer` 加载；
- 粗配准到精配准的交接通过 artifact id 完成，不依赖服务器文件路径或 base_software 的文本缓存文件。

浏览器不具备 WebGL2 时，任务仍然可以正常完成并下载；只是三维预览会显示明确的能力错误。

## 与 base_software 的差异

算法参数、输出命名和数值行为以 base_software 为基线，但文件交互模型完全不同：

- 当前使用浏览器上传/会话 artifact，不使用 Tk 对话框。
- 当前使用 `data/sessions/<uuid>/artifacts/` 与 `session.json`，不写 `Tool_*` 文本路径缓存。
- 当前每个任务使用独立 work 目录，结果由 runner 登记；失败原因通过任务 API 显式返回。
- 结果预览和下载在浏览器中完成，不调用 `os.startfile` 打开服务器目录。

## 相关页面

- [会话、上传与产物工作流](session-upload-and-artifacts.md)
- [异步任务执行与进度](async-job-execution.md)
- [点云处理算法与基线约束](../algorithms/point-cloud-processing.md)
- [点云预览管线](../architecture/point-cloud-preview-pipeline.md)
- [快速开始](../quickstart.md)
