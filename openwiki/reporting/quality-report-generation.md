---
type: reporting-workflow
title: 质量报告生成与工具链
description: 说明尺寸质量评估的 PyVista 图片、Plotly/Kaleido 直方图、PyLaTeX 组装、latexmk/xelatex 编译、PDF 命名及相对 base_software 的显式版式适配。
tags: [reporting, visualization, pdf, latex, kaleido]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-5d593278ee6c8f05c76ca7b5
    resource: repo://backend/app/api/artifacts.py
  - id: openwiki-source-115bc96dd839c419e53a5004
    resource: repo://backend/app/report/figures.py
  - id: openwiki-source-7de602f3229bbc366ae0b3b4
    resource: repo://backend/app/report/pdf.py
  - id: openwiki-source-29449cdcdd8456fbc5b9b089
    resource: repo://backend/app/services/quality.py
  - id: openwiki-source-1771024592351e13dbb973b9
    resource: repo://backend/docs/report-toolchain.md
  - id: openwiki-source-519b320cda3dc2bab0b3ad68
    resource: repo://backend/tests/test_report_module.py
  - id: openwiki-source-1261108d77ca574ba4899ab8
    resource: repo://backend/tests/test_report_toolchain.py
  - id: openwiki-source-65886542f381702f729185bd
    resource: repo://base_software/functions/draw_functions.py
  - id: openwiki-source-b735a19d109c0dd7887674e9
    resource: repo://base_software/functions/PDF.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 质量报告生成与工具链

## 报告链路

B/S 质量评估在后台任务中按固定顺序生成图片，再由 PyLaTeX 组装并编译 PDF：

```text
读取点云
  -> PyVista 离屏截图
  -> Plotly 偏差直方图 + Kaleido 导出
  -> PyLaTeX 组装 LaTeX
  -> latexmk -xelatex 编译 PDF
  -> 登记 report artifact，浏览器下载
```

中间图片写在任务工作目录的 `cache/` 中，成功产物由任务完成回调登记到当前会话。报告生成失败时任务状态为 failed，页面显示失败原因，不登记 PDF 产物。

## 固定图片

质量评估服务会生成以下固定名称的文件：

| 阶段 | 生成方式 | 文件 |
| --- | --- | --- |
| 读取扫描点云 | PyVista 离屏截图 | `fig1a.jpg` |
| 读取 BIM/离散点云 | PyVista 离屏截图 | `fig1b.jpg` |
| 两种输入叠加 | PyVista 离屏截图 | `fig2.jpg` |
| 剔除环境后的扫描点云 | PyVista 离屏截图 | `fig3.jpg` |
| 提取后的检测点 | PyVista 离屏截图 | `fig4.jpg` |
| 偏差云图 | PyVista + Matplotlib seismic 色图 | `fig5.jpg` |
| 偏差分布直方图 | Plotly + Kaleido | `Error_Analysis.jpg` |

固定文件名意味着同一任务工作目录会覆盖同名文件；但每个任务有独立 `work/<job_id>/cache`，不会跨任务互相覆盖。

## 偏差云和直方图语义

`figures.draw_error2()` 把偏差按降序排列，并把前 `int(检测点数 × ratio)` 个点的标量显示值置为 0；点本身仍保留在图中。`figures.show_clum()` 以 1 mm 为步长构造直方图区间，在剔除线位置绘制红色虚线，并标注检测点数、剔除线、最大值、平均值和中位数。

质量评估服务先把偏差乘以 `1000` 作为 mm 统计，再把同一组结果传给报告和前端预览。页面指标、直方图 JSON 和 PDF 都来自同一次后台任务，避免不同链路使用不同口径。

## PDF 结构

`backend/app/report/pdf.py` 的 `QA_Report()` 生成中文文档，结构包括：

1. 封面：点云名、报告名、产品名和当天日期。
2. 页眉页脚：产品名、报告名和页码。
3. “基本信息”：四个前置确认、扫描/BIM 路径、参数表、图 1/图 2。
4. “方法流程”：固定技术路线说明，插入图 3/图 4。
5. “尺寸评估结果”：偏差云图、偏差柱状图和统计指标表。

方法流程文本是固定描述，不会根据本次实际执行了哪些预处理步骤动态改写；报告仍描述推荐的完整技术路线。

## Linux 报告工具链

Linux 上的报告链路依赖：

- PyVista 离屏截图环境（DISPLAY、EGL/OSMesa 或 xvfb）。
- Plotly + Kaleido，并由 Chrome/Chromium 导出图片。
- PyLaTeX，加载 `ctex`、`indentfirst`、`float` 等包。
- `latexmk` 与 `xelatex`，以及 ctex/Fandol 中文字体和相关宏包。

`backend/docs/report-toolchain.md` 提供了用户级 TinyTeX 安装步骤。相对 base_software，当前后端有三项经过批准的显式适配：

- **xelatex**：`generate_pdf` 使用 `compiler='latexmk'`、`compiler_args=['-xelatex']`，因为 ctex 的 Fandol 字体集不能在 pdfTeX 下正常使用，同时保留多轮编译以解析页码引用。
- **360pt**：基线中的 `width='360px'` 是非法 LaTeX 单位，实际恢复后按 pt 处理；后端显式写成 `360pt`，版式与错误恢复结果一致。
- **圈号字形**：加入 `\xeCJKDeclareCharClass{CJK}{"2460 -> "24FF}`，把 ①-⑥ 等圈号映射到中文字体，避免缺字形。

这些是报告工具链的平台适配，不是数值算法修复。

## 命名与清理

报告文件名由以下部分组成：

```text
<点云主名>几何质量评估报告<YYYY><M><D>.pdf
```

月份和日期不补零，也不包含时分秒。服务把报告登记为 `kind=report` 的产物，但报告文件本身没有额外的版本后缀；同名扫描点云在一年同一天生成时可能使用相同显示名。PDF 编译使用 `clean_tex=True`，成功/失败过程中的中间文件在指定编译流程中会被清理或留在任务工作目录。

## 失败与验证

报告任务可能失败在以下边界：

- `/api/health` 报告缺少 TeX、Chromium、离屏渲染或字体依赖。
- PyVista 截图或 Kaleido 导出失败。
- LaTeX 编译失败，错误由任务层显式返回。
- 输入点云无法读取、参数非法或计算阶段产生非有限值。

`test_report_module.py` 在无 TeX 环境下验证图片和 LaTeX 源生成；`test_report_toolchain.py` 在 `latexmk`/`xelatex` 可用时编译真实 PDF，确认文件以 `%PDF` 开头、大小超过 20 KB 且 `clean_tex=True` 不留下 `.tex`。缺少 TeX 时该测试会跳过，部署环境仍必须通过 `/api/health` 检查依赖。

## 相关页面

- [尺寸质量评估 B/S 工作流](../workflows/dimension-quality-assessment.md)
- [点云处理算法与基线约束](../algorithms/point-cloud-processing.md)
- [测试、Golden 基线与端到端验收](../development/testing-and-golden-parity.md)
- [B/S 运行、依赖与部署](../operations/runtime-and-deployment.md)
