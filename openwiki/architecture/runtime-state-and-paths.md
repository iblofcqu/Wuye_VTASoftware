---
type: runtime-architecture
title: 运行时状态与路径
description: 说明应用根目录和缓存目录的解析方式、文本缓存文件构成的跨页面状态协议，以及重跑、缺失文件、取消选择和平台差异带来的行为。
tags: [architecture, state, filesystem, packaging]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:28:45.133Z
sources:
  - id: openwiki-source-b735a19d109c0dd7887674e9
    resource: repo://base_software/functions/PDF.py
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

# 运行时状态与路径

## 应用根目录

`path_utils.get_app_base_path()` 提供两种环境下的统一根目录：

- PyInstaller 等冻结环境返回 `sys._MEIPASS`。
- 源码环境先检查当前文件目录是否同时存在 `pages`、`functions`、`interface`，不存在时向父目录逐层查找；仍未命中时返回 `path_utils.py` 所在目录。

缓存、界面资源、函数和页面路径都从这个根目录派生。当前仓库没有跟踪 `interface` 目录，因此源码运行虽然可以得到 `base_software` 根路径，但只有补齐 `interface/CMGC.png`、`logo.png` 和 `TJBridge.png` 后首页才能完整渲染。

## 缓存目录

`get_cache_path()` 会在根目录下按需创建 `cache/`；首页启动时也会主动执行同样的初始化。缓存目录同时承担三种职责：

1. 保存用户通过 Tk 对话框选择的输入、输出路径。
2. 在预处理工具之间交接生成文件路径。
3. 保存质量评估用于生成报告和界面预览的固定名称图片。

## 文本状态文件

应用没有使用数据库、`st.session_state`、pickle 或结构化配置。页面把纯文本路径直接写入文件，下一次 Streamlit 重跑或另一个工具再读取。主要文件如下：

| 范围 | 文件 | 内容 |
| --- | --- | --- |
| 网格离散 | `Tool_BIM2PCD_Input.txt` / `Tool_BIM2PCD_Output.txt` | 网格文件和输出目录 |
| 尺寸缩放 | `Tool_Scale_Input.txt` / `Tool_Scale_Output.txt` | 输入文件和输出目录 |
| 体素下采样 | `Tool_Sampling_Voxel_Input.txt` / `Tool_Sampling_Voxel_Output.txt` | 输入文件和输出目录 |
| 均匀下采样 | `Tool_Sampling_Uniform_Input.txt` / `Tool_Sampling_Uniform_Output.txt` | 输入文件和输出目录 |
| FPFH 粗配准 | `Tool_Registration_FPFH_SCENE.txt`、`_BIM.txt`、`_Output.txt` | 移动点云、固定点云、输出目录 |
| 精配准 | `Tool_Registration_ICP_SCENE.txt`、`_BIM.txt`、`_Output.txt` | 移动点云、固定点云、输出目录 |
| 质量评估 | `QA_pcd.txt`、`QA_BIM.txt`、`QA_Report.txt` | 扫描点云、BIM 点云、报告目录 |

每次重新选择都会覆盖对应文件；文件内容没有版本号、JSON 结构或并发锁。多个浏览器会话共享同一个文件系统缓存，因此后一个会话的选择可以覆盖前一个会话尚未执行完的路径。

## 跨页面交接

FPFH 粗配准成功后把结果保存为 `<扫描点云名>_FPFH.xyz`，并立即把该结果路径写进 `Tool_Registration_ICP_SCENE.txt`。进入精配准页面后，如果用户不重新选择移动点云，按钮逻辑会读取这个缓存路径作为默认输入。这个交接仍以磁盘路径为唯一媒介，并没有把点云对象或变换矩阵保留在内存中。

质量评估页不会自动读取预处理的 FPFH 或 ICP 输出；它只读取用户通过 `QA_pcd.txt` 保存的扫描点云路径。

## 可观察的失败与边界

- 点云计算按钮通常会直接读取前置缓存文件。如果用户尚未选择路径，代码会抛出 `FileNotFoundError`；这些核心计算入口大多没有把缺失文件转换成友好提示。
- Tk 文件对话框取消时通常返回空字符串，但页面仍会把空字符串写入缓存。后续读取不会把空路径识别为“取消”，而是在点云读取或保存阶段失败。
- 固定图片名会在每次质量评估时覆盖，包括 `fig1a.jpg`、`fig1b.jpg`、`fig2.jpg`、`fig3.jpg`、`fig4.jpg`、`fig5.jpg` 和 `Error_Analysis.jpg`。报告模块随后从同一缓存目录读取这些文件。
- 网格离散的“打开输出文件夹”按 Windows、macOS、Linux 分支处理；精配准和质量评估的同类按钮直接调用 `os.startfile`，平台兼容性不一致。
- 精配准的“打开输出文件夹”把 `cache_path` 与字符串 `/Tool_Registration_FPFH_Output.txt` 拼接。前导斜杠会使该字符串成为绝对路径，因而优先读取文件系统根目录而不是缓存目录中的文件。
