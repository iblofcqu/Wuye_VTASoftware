---
type: architecture-overview
title: 应用架构总览
description: 说明 DeviScan-3D 的 Streamlit 入口、内置 pages 导航、两条业务页面链路、共享算法与报告模块之间的职责边界。
tags: [architecture, streamlit, application]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:28:45.133Z
sources:
  - id: openwiki-source-d69beca5a040440e55fef3c1
    resource: repo://base_software/home_page.py
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
  - id: openwiki-source-f62fb78e9932aaca3ecc6806
    resource: repo://base_software/path_utils.py
generated: { by: "codex", at: "2026-09-28T07:28:45.133Z" }
---

# 应用架构总览

## 入口与页面拓扑

`base_software/home_page.py` 是启动时应交给 Streamlit 的主入口。它设置首页标题、图标、布局和菜单信息，初始化 `cache` 目录，并读取 `interface` 下的 `CMGC.png`、`logo.png` 与 `TJBridge.png` 作为品牌页面。`home_page.py` 本身不执行点云计算，只承担应用外壳和功能导航。

目录中的 `base_software/pages/` 使用 Streamlit 的内置多页面约定：

- `1_🛠️_点云预处理.py` 面向点云准备和配准。
- `2_🖥️_尺寸质量评估.py` 面向偏差计算、统计与报告生成。

因此应用有两层导航：Streamlit 负责在首页和两个页面之间切换，页面脚本内部再用 `st.sidebar.radio` 选择具体工具或模式。

## 页面职责

### 点云预处理

点云预处理页把一组相对独立的工具集中在一个脚本中，侧边栏入口包括说明书、网格离散、尺寸缩放、下采样和配准。页面负责：

- 用 Tk 文件对话框选择输入、输出路径。
- 校验网格离散和部分数值参数。
- 调用 `functions` 中的算法模块。
- 用 PyVista/stpyvista 显示输入或处理结果。
- 将点云结果和后续交接所需的路径写入 `cache` 文件。

其中“配准”又分为 FPFH 粗配准和三次 ICP 精配准。粗配准成功后，保存路径会被写入 ICP 页面默认读取的缓存文件，形成页面内的建议交接关系。

### 尺寸质量评估

尺寸质量评估页把预处理结果作为前置条件。它先要求用户确认已有离散点云、单位一致性、必要下采样和已完成匹配，再允许选择扫描点云、BIM 点云和报告目录。

计算链由页面直接编排：

1. 读取两侧点云并生成输入预览。
2. 用 BIM 点云邻近关系剔除扫描环境，再从 BIM 点云中提取与扫描结果重合的检测点。
3. 选择 Point2Point 或 Point2Plane 计算偏差。
4. 按比例确定剔除线和统计指标，绘制偏差图。
5. 调用报告模块生成 PDF，并把中间图片写入缓存目录。

## 模块边界

页面脚本是工作流编排层，`functions` 目录是计算与输出层：

| 模块 | 主要职责 |
| --- | --- |
| `load_data.py` | 读取 xls/xyz/asc/txt、创建目录、列出文件 |
| `Poisson_Disk_Sampling.py` | 网格到点云的离散化 |
| `down_samples.py` | 体素、均匀、最远点和随机下采样 |
| `FPFH.py` | 体素、法向量、FPFH 特征和 RANSAC 粗配准 |
| `Registration.py` | 球体检测、变换矩阵、球心配准与 ICP |
| `knn.py` | KDTree 邻域筛选、偏差计算、平面拟合 |
| `draw_functions.py` | PyVista 预览/截图与 Plotly 偏差直方图 |
| `PDF.py` | 组装 LaTeX 报告并调用 PDF 编译 |

页面通过通配符从多个 `functions` 模块导入函数，算法模块之间也直接横向调用。这种组织方式适合当前小型单体应用，但模块边界主要靠命名而不是接口约束维持。

## 状态与耦合

应用没有显式服务层或数据库。页面计算产生的点云以 `.xyz` 文件落盘，页面之间和 Streamlit 重跑之间则通过 `cache` 下的文本文件交接路径与参数。关键结果不会自动从预处理页流向评估页：用户仍需在评估页重新选择已经生成的配准点云。

公共根目录、缓存目录和界面资源目录由 `path_utils.py` 统一解析；该模块同时兼容普通源码运行和 `sys.frozen` 打包运行。
