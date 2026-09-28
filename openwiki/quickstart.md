---
type: quickstart
title: 快速开始
description: 面向首次运行者，概括 DeviScan-3D 的能力、启动前提、两条业务工作流、主要本地文件限制和 OpenWiki 手动维护方式。
tags: [quickstart, streamlit, point-cloud, quality-assessment]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:42:19.658Z
sources:
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-b735a19d109c0dd7887674e9
    resource: repo://base_software/functions/PDF.py
  - id: openwiki-source-d69beca5a040440e55fef3c1
    resource: repo://base_software/home_page.py
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
  - id: openwiki-source-5f29572408b9e8962311ba6a
    resource: repo://base_software/README.md
  - id: openwiki-source-7f0ef148148cf22231d1845e
    resource: repo://base_software/requirements.txt
  - id: openwiki-source-f317ee207e1653d2033c81a4
    resource: repo://CONTRIBUTING.md
generated: { by: "codex", at: "2026-09-28T07:42:19.658Z" }
---

# 快速开始

## 这是什么

`base_software` 是一个基于 Streamlit 的三维扫描分析演示应用，主要处理两类任务：

1. 把 BIM 网格转换为点云，并按需进行单位缩放、下采样、FPFH 粗配准和 ICP 精配准。
2. 比较扫描点云与 BIM 离散点云，计算几何偏差、生成偏差云图和统计指标，再输出中文 PDF 报告。

首页入口是 `home_page.py`。Streamlit 自动识别 `pages/` 下的两个功能页，因此启动入口后应能在侧边导航中进入“点云预处理”和“尺寸质量评估”。

## 运行前检查

从仓库根目录启动时，常规入口命令是：

```bash
streamlit run base_software/home_page.py
```

仓库没有提交启动脚本、Docker 配置、环境锁或服务定义，因此这条命令仍需在目标环境验证。运行前至少需要：

- 安装 `base_software/requirements.txt` 中的 Python 依赖。
- 提供 `base_software/interface/CMGC.png`、`logo.png`、`TJBridge.png`。当前版本库未跟踪 `interface` 目录，缺少这些文件时首页不能完整渲染。
- 准备可写目录。应用会在 `base_software/cache/` 保存路径、图片和中间状态。
- 使用本地桌面会话，因为文件选择依赖 Tk 对话框。
- 安装支持中文 `ctex` 包的 LaTeX 工具链；项目 README 还声明完整运行需要 TeXstudio 和 Google Chrome。
- 注意运行清单指定 Python 3.10.18，而 `prek` 使用 Python 3.11；部署前应由维护者确认统一版本。

应用不使用浏览器上传控件选择核心输入。文件对话框打开在运行 Streamlit 的电脑上，远程用户无法借此浏览自己的本地文件。

## 推荐业务路径

### 1. 准备 BIM 点云

进入“点云预处理 -> 网格离散”，选择 STL、PLY、OBJ、OFF、GLTF 或 GLB 网格，设置点间距并输出 `.xyz`。若扫描数据和 BIM 单位不一致，随后使用“尺寸缩放”转换到同一单位。

### 2. 按需轻量化

需要降低点数时使用体素下采样或均匀下采样。三维质量评估内部仍会以固定 `0.1` 体素再次处理 BIM 点云，因此预处理下采样不是质量评估的硬前置条件。

### 3. 对齐两类点云

先在“配准 -> 粗配准”中使用 FPFH 配准移动点云和固定点云。程序会保存 `_FPFH.xyz`，并把路径写入精配准的默认移动点云缓存。检查预览后，再进入“配准 -> 精配准”完成三次 ICP，输出 `_ICP.xyz`。

这仍是一套人工工作流：粗配准是否可接受需要用户检查，质量评估也不会自动读取预处理生成的 `_FPFH.xyz` 或 `_ICP.xyz`。

### 4. 计算尺寸质量

进入“尺寸质量评估”，依次确认离散点云、单位一致性和匹配状态，然后选择：

- 已配准的扫描点云。
- BIM/离散点云。
- 报告保存目录。
- 点云单位。
- `Point2Point` 或 `Point2Plane`。
- 平面邻域大小和最大偏差剔除比例。

页面会执行环境点云剔除、缺失区筛选、偏差计算、直方图统计和 PDF 输出。偏差在显示和统计前由输入单位乘以 1000 转为 mm。

## 选择偏差方法

- `Point2Point`：计算检测点到扫描点云的最近点距离，结果受扫描点间距影响。
- `Point2Plane`：在最近扫描点邻域内拟合局部平面，再计算点到平面的距离。邻域不足 3 个点时当前实现把偏差记为 0。

`distance` 标签说明主要服务 Point2Plane，但它也会通过 `distance × 10` 影响环境点剔除，所以切换为 Point2Point 后仍不应忽略该参数。

## 结果文件

- 预处理点云：用户所选目录下的 `_FPFH.xyz`、`_ICP.xyz`、`_VD.xyz`、`_UD.xyz` 或单位后缀文件。
- 评估中间图：`cache/fig1a.jpg`、`fig1b.jpg`、`fig2.jpg`、`fig3.jpg`、`fig4.jpg`、`fig5.jpg` 和 `Error_Analysis.jpg`。
- 报告：报告目录下以扫描点云主名和“几何质量评估报告年月日”命名的 PDF。

固定图片名和只精确到日期的报告名都可能覆盖较早结果。

## 已知限制

- 当前源码没有自动化业务测试；`prek` 只覆盖格式、文档、代码拼写、密钥和提交信息。
- 服务器部署后，Tk 文件对话框和 Windows 专用的 `os.startfile` 与浏览器客户端模型不匹配。
- 参数范围、空点云和缺失缓存文件缺少统一校验，失败会表现为底层库异常。
- 当前仓库已有 25 页 Word 使用说明书和外部 DeviScan3D 压缩包链接，但源码仍是 Streamlit 单体应用，没有完成 README 中讨论的重新选型或服务器化改造。

## 仓库文档维护

本仓库是私有仓库，没有配置 GitHub Actions，也不需要定时工作流来维护 OpenWiki。不要创建或恢复 `.github/workflows/openwiki-update.yml`，也不要为该流程配置 Actions secrets。OpenWiki 初始化或更新由维护者在本地显式执行，生成结果按普通文档改动审查和提交。

更多维护约束见[开发与质量流程](development/quality-workflow.md)。

## 继续阅读

- [应用架构总览](architecture/application-overview.md)
- [运行时状态与路径](architecture/runtime-state-and-paths.md)
- [点云预处理工作流](workflows/point-cloud-preprocessing.md)
- [尺寸质量评估工作流](workflows/dimension-quality-assessment.md)
- [点云处理算法](algorithms/point-cloud-processing.md)
- [可视化与质量报告生成](reporting/quality-report-generation.md)
- [运行、依赖与部署](operations/runtime-and-deployment.md)
- [开发与质量流程](development/quality-workflow.md)
