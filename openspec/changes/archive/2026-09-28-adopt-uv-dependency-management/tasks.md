# Tasks

## 1. uv 项目清单

- [x] 1.1 新增 `base_software/pyproject.toml`，设置项目元数据、`requires-python = ">=3.10.18,<3.11"`、运行时直接依赖、Windows `pywin32` marker、`build` dependency group、`[tool.uv].package = false` 和默认 Aliyun PyPI index；运行 `uv lock --directory base_software --python 3.10.18 --default-index https://mirrors.aliyun.com/pypi/simple --refresh`，确认 TOML 可解析且解析成功。
- [x] 1.2 新增 `base_software/.python-version`，内容为 `3.10.18`；运行 `uv python find 3.10.18 --directory base_software`，确认得到 3.10.18 解释器。
- [x] 1.3 检查 `base_software/uv.lock`，确认 `open3d`、`numpy`、`streamlit`、`pyvista`、`stpyvista`、`kaleido`、`pyransac3d`、`pyinstaller` 和条件包 `pywin32` 均按设计解析；运行 `uv lock --check --directory base_software`，确认锁文件与 `pyproject.toml` 一致。
- [x] 1.4 运行 `uv tree --directory base_software`，确认依赖树不包含未使用的 TensorFlow、Keras、OpenCV 和 TensorBoard 顶层依赖；若出现，只保留为真实传递依赖并在设计说明中记录，不手工复制完整环境导出。

## 2. 环境与运行时门禁

- [x] 2.1 在 Linux 环境运行 `uv sync --frozen --directory base_software`，确认项目配置使用 Aliyun index，确认创建项目虚拟环境、安装成功且不安装 `pywin32`；同时确认生成的解释器满足 Python 3.10.18。
- [x] 2.2 从 `base_software` 运行 `uv run python -c "import numpy, open3d, pandas, PIL, plotly, kaleido, pyvista, stpyvista, matplotlib, sklearn, scipy, pylatex, pyransac3d, tqdm, streamlit"`，确认所有直接依赖可导入。若失败原因是既有 Open3D/NumPy 版本组合，停止实施并提交版本决策问题，不擅自升级或降级。
- [x] 2.3 从 `base_software` 运行 `uv run python -c "import functions.FPFH, functions.PDF, functions.load_data, functions.knn, functions.Registration"`，确认核心业务模块在 uv 环境中可导入。
- [x] 2.4 从 `base_software` 运行 `uv run python -m compileall -q .`，确认所有 Python 文件通过语法编译。
- [x] 2.5 从仓库根目录运行 `prek run --all-files`，确认格式、Markdown、密钥扫描和提交信息门禁全部通过。

## 3. 文档迁移

- [x] 3.1 更新 `base_software/README.md`，将依赖安装和启动说明改为 `cd base_software && uv sync --frozen && uv run streamlit run home_page.py`，并说明打包时使用 `--group build`。
- [x] 3.2 在 README 中记录 Python 3.10.18、首次运行需要联网下载解释器和依赖、根目录 `prek` 的 Python 3.11 与应用运行时相互独立；人工检查命令与实际 uv 文件一致。
- [x] 3.3 删除 `base_software/requirements.txt`；运行 `rg -n "requirements\\.txt|pip install -r" base_software CONTRIBUTING.md`，确认不再存在旧安装入口引用。

## 4. 变更提交

- [x] 4.1 只暂存 `base_software/pyproject.toml`、`base_software/.python-version`、`base_software/uv.lock` 和根目录 `.gitignore`，复核 `git diff --cached` 后提交 `build: 采用 uv 管理基础软件依赖`，并确认提交钩子通过。
- [x] 4.2 暂存 README 更新和 `requirements.txt` 删除，复核 `git diff --cached` 后提交 `build!: 移除 requirements.txt 并改用 uv`，并在提交正文说明迁移命令与回滚方式；确认提交钩子通过。

## 5. 最终验证

- [x] 5.1 从干净工作区再次运行 `uv lock --check --directory base_software`、`uv sync --frozen --directory base_software`，确认项目配置使用 Aliyun index 和任务 2.2 的导入命令，确认结果可复现。
- [x] 5.2 运行 `openspec validate adopt-uv-dependency-management --strict`，确认 proposal、design、tasks 以及 `skip_specs` 配置通过校验。
- [x] 5.3 运行 `git status --short`，确认不存在未提交的 `base_software` 迁移文件，且 `.venv` 或 `__pycache__` 等环境产物已被忽略；失败时修正后再结束。
