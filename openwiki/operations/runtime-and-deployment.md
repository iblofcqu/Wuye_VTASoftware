---
type: operations-guide
title: 运行、依赖与部署
description: 汇总 Streamlit 入口、Python 与系统依赖、本地桌面耦合、缓存写权限、中文 PDF 工具链和项目已知服务器部署限制。
tags: [operations, deployment, dependencies, windows]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:28:45.133Z
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
  - id: openwiki-source-f62fb78e9932aaca3ecc6806
    resource: repo://base_software/path_utils.py
  - id: openwiki-source-5f29572408b9e8962311ba6a
    resource: repo://base_software/README.md
  - id: openwiki-source-7f0ef148148cf22231d1845e
    resource: repo://base_software/requirements.txt
generated: { by: "codex", at: "2026-09-28T07:28:45.133Z" }
---

# 运行、依赖与部署

## 启动入口

应用以 Streamlit 脚本形式运行，`base_software/home_page.py` 是首页入口，`base_software/pages/` 提供两个内置页面。仓库没有启动脚本、Dockerfile、服务定义、环境锁文件或独立 Python 包配置，运行者需要自行提供 Streamlit 启动命令和可导入 `base_software` 的工作目录。

源码路径假设应用根目录同时包含 `pages`、`functions` 和 `interface`。当前版本库没有跟踪 `interface` 目录，但首页会读取其中的 `CMGC.png`、`logo.png` 与 `TJBridge.png`；缺少这些资源时首页不能完成渲染。

## Python 依赖

`base_software/requirements.txt` 使用 `~=` 列出大量带近似版本的依赖，其中包括：

- Streamlit、Plotly、Kaleido 和 stpyvista。
- Open3D、NumPy、SciPy、scikit-learn、scikit-image 和 pyransac3d。
- PyVista、VTK、Matplotlib 和 pandas。
- Pillow、Tk 相关运行环境以及 PyInstaller。
- PyLaTeX 和 TensorFlow 等未在当前页面调用链中直接需要的包。
- `pywin32`、Python 本身、zlib 和 openssl 等由环境或操作系统提供的条目。

该文件更像完整环境导出而不是最小依赖清单，也没有针对不同操作系统的 marker。`requirements.txt` 指定 `python~=3.10.18`，而根目录 `prek` 配置使用 Python 3.11；这是当前运行环境和开发门禁之间的显式版本冲突，部署前需要由项目维护者确认应统一到哪个版本。

## 本地桌面与平台耦合

两个页面在模块初始化时创建隐藏的 Tk 根窗口，并通过 Tk 文件对话框选择输入文件或输出目录。文件浏览发生在运行 Streamlit 的计算机上，而不是访问浏览器的远程客户端上；因此把进程部署到服务器后，远程用户无法用该对话框浏览自己的本地文件。

打开输出目录的实现并不统一：

- 网格离散页按 Windows、macOS、Linux 分别调用 `os.startfile`、`open` 或 `xdg-open`。
- 尺寸缩放、下采样、配准和尺寸质量评估页面直接调用 `os.startfile`，实际运行依赖 Windows。
- 精配准还存在缓存文件名前导斜杠导致的错误路径。

## 文件与权限

应用需要读取输入点云，并在以下位置写文件：

- 用户选择的点云或报告输出目录。
- 应用根目录下的 `cache/`。
- PyLaTeX 生成 PDF 时产生的临时 `.tex`、日志和辅助文件。

在普通源码环境中，缓存位于 `base_software/cache/`；在冻结环境中，路径从 `sys._MEIPASS` 派生。部署目录没有写权限时，路径保存、图片截图和报告生成都会失败。

## 报告工具链

报告模块使用 PyLaTeX，并加载 `ctex`、`indentfirst` 和 `float` 三个 LaTeX 包，最后调用 `generate_pdf`。因此除了 Python 依赖外，运行环境还需安装可生成中文 PDF 的 LaTeX 发行版。项目 README 另外声明完整运行需要 TeXstudio 和 Google Chrome；其中 Chrome/Kaleido 与 Plotly 图片导出的运行环境有关，LaTeX 编译器则直接由报告生成代码调用。

## 打包与服务器部署现状

`base_software/README.md` 记录了 DeviScan3D 压缩包和外部网盘分发方式，也记录了项目已经意识到的部署问题：

- 软件可能被解压到服务器上运行。
- 局域网用户访问时，上传/选择功能仍指向部署机器本地文件。
- 服务器端文件浏览框无法看到客户端文件目录。
- 当前方案存在改用其他框架、重新开发的讨论，但仓库没有相应的迁移实现或部署配置。

这些是产品与部署待决事项，不应被描述为已经由当前代码解决。当前代码可保证的仍是“在具备桌面文件对话框、依赖工具和写权限的本地 Windows 环境中运行单体 Streamlit 应用”。
