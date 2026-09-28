---
type: reporting-workflow
title: 可视化与质量报告生成
description: 说明尺寸质量评估中的 PyVista/Plotly 中间图片、偏差统计指标、PyLaTeX/ctex 报告结构和最终 PDF 文件命名契约。
tags: [reporting, visualization, pdf, latex]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:28:45.133Z
sources:
  - id: openwiki-source-65886542f381702f729185bd
    resource: repo://base_software/functions/draw_functions.py
  - id: openwiki-source-b735a19d109c0dd7887674e9
    resource: repo://base_software/functions/PDF.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
generated: { by: "codex", at: "2026-09-28T07:28:45.133Z" }
---

# 可视化与质量报告生成

## 可视化顺序

尺寸质量评估页在同一缓存目录中生成一组固定名称图片，报告模块随后按这些名称装配文档：

| 阶段 | 生成方式 | 文件 |
| --- | --- | --- |
| 读取扫描点云 | PyVista 离屏截图 | `fig1a.jpg` |
| 读取 BIM/离散点云 | PyVista 离屏截图 | `fig1b.jpg` |
| 两种输入点云叠加 | PyVista 离屏截图 | `fig2.jpg` |
| 剔除环境后的扫描点云 | PyVista 离屏截图 | `fig3.jpg` |
| 提取后的检测点 | PyVista 离屏截图 | `fig4.jpg` |
| 偏差云图 | PyVista + Matplotlib `seismic` 色图 | `fig5.jpg` |
| 偏差分布直方图 | Plotly 图，Kaleido 写为 PNG 文件 | `Error_Analysis.jpg` |

固定文件名意味着相同缓存目录内的下一次评估会覆盖上一次图片。报告生成必须与这些截图在同一轮页面执行中衔接，否则会使用旧图片或直接找不到文件。

## 偏差云图

Page 2 先把偏差乘以 1000，使数值以 mm 进入显示和报告。`show_error` 与 `draw_error2` 会按偏差从大到小排序，并把前 `int(检测点数 × ratio)` 个点的标量值设为 0；点本身仍保留在图中，但最大偏差部分不再使用其真实颜色显示。这与统计指标中的“剔除比例”一致，但不是从点数组中物理删除。

如果 `ratio` 为 1，统计阶段的 `line_number` 会等于数组长度并导致索引越界；当前页面只把输入文本转成浮点数，没有校验 `0 ≤ ratio < 1` 或空结果集。

## 直方图与统计

`show_clum` 用步长 1 mm 构造偏差区间，利用 NumPy 计算频数，再创建 Plotly 柱状图。图中包含一条位于“剔除部分点后最大偏差”位置的红色虚线，并标注检测点数、剔除线、最大值、平均值和中位数。

页面另外写入报告字典的统计值包括：

- `check_num`：检测点数量。
- `error_max_cut`：排序后位于剔除线上的偏差。
- `error_max`：未剔除时的最大偏差。
- `error_mean`：全部偏差的算术平均值。

这些值先从 mm 浮点数格式化为两位小数，再传回浮点数。原始输入点云点数、单位、偏差方法、平面邻域大小和剔除比例也会进入报告。

## PDF 文档结构

`QA_Report` 使用 PyLaTeX 创建文档，并加载：

- `ctex`：中文排版。
- `indentfirst`：中文首段缩进。
- `float`：图片位置控制。

报告结构依次为：

1. 自动生成封面，包含点云名、报告名称、产品名称和当天日期。
2. 页眉页脚，包含产品名、报告名和页码。
3. “基本信息”：输入路径、点云单位、偏差方法、平面邻域大小、剔除比例、两侧点云点数，以及图 1/图 2。
4. “方法流程”：说明网格离散、FPFH/RANSAC 粗配准、三次 ICP、环境点剔除、缺失点剔除、Point2Point/Point2Plane 和最大偏差剔除思路，并插入图 3/图 4。
5. “尺寸评估结果”：插入偏差云图、偏差柱状图和图 2 的统计指标表。

技术路线段落是固定说明文本，不会根据用户实际选择的半自动步骤动态改写；即使本次没有实际执行网格离散或配准，报告仍描述完整推荐流程。

## 输出与覆盖风险

最终文件名由报告目录、扫描点云主文件名、固定后缀“几何质量评估报告”和年月日拼接而成：

```text
<output_path>/<PCD_name>几何质量评估报告<YYYY><M><D>.pdf
```

月份和日期不补零，文件名也没有小时、分钟或秒。同一天、同名扫描点云再次生成报告时会使用相同输出路径，存在覆盖或编译冲突风险。`clean_tex=True` 会在生成后清理 LaTeX 中间文件，但 PDF 生成仍要求目标目录可写并安装 `ctex` 对应的 TeX 工具链。
