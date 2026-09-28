# Wuye_VTASoftware

五冶预拼拼装软件项目。界面通过 Streamlit 展示，使用 uv 管理 Python 依赖，从 `home_page.py` 启动。

## 环境与依赖

- Python 3.10.18，由 uv 根据 `.python-version` 管理。
- 首次同步需要联网下载 Python 解释器和依赖包。
- `pyproject.toml` 和 `uv.lock` 是唯一依赖源，默认使用 Aliyun PyPI 镜像。
- 完整运行需在电脑中安装 TeXstudio（用于生成 PDF 报告）以及 Google Chrome。
- 根目录 `prek` 使用 Python 3.11，只负责代码检查，与应用运行时 3.10.18 相互独立。

## 本地运行

```bash
cd base_software
uv sync --frozen
uv run streamlit run home_page.py
```

## 打包依赖

PyInstaller 位于独立的 `build` dependency group。需要打包时执行：

```bash
cd base_software
uv sync --frozen --group build
```

## 项目背景

25 年为五冶申请的软著，如今需要嵌入他们的系统。除 `home_page.py` 外，项目包含 `pages` 文件夹中的点云预处理和尺寸质量评估界面。

压缩包 DeviScan3D 为打包的软件，包含了所有的包，解压该文件运行 `.exe` 可直接运行。五冶当前本身有一个系统，他们自己在系统加了个按钮，链接到 `.exe` 文件，但部署在服务器上。

已知问题：

1. 该软件解压在他们的服务器上。
2. 通过局域网进入软件时，上传文件功能只链接了本地文件，即只可浏览部署电脑上的文件。
3. 通过局域网访问时，界面浏览文件框看不到文件目录。

针对上述问题，五冶想看看能不能重新打包（即 `functions` 文件夹、`pages` 文件夹、`home_page.py`、`path_utils.py` 以及相关包），东声和马哥让软件工程师评估一下打包工作量再做决定。廖岳认为这个 demo 是围绕 Streamlit 做的，要重新打包解决上述问题，应该要用别的框架，不单单是重新打包，需要重新编软件，具体功能可查看 `3使用说明书-基于点云预拼装的结构构件尺寸质量评定系统.doc`。
