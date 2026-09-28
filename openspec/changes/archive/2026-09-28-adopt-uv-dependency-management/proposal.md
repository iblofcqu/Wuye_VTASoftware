# Proposal

## Why

`base_software/requirements.txt` 是包含 107 个条目的环境导出，混合了直接依赖、传递依赖、构建工具、Windows 专用包以及 `python`、`zlib`、`openssl` 等非 Python 依赖。它无法单独表达 Python 版本、平台 marker、开发/构建依赖组，也没有锁文件保证解析结果一致。

当前 demo 需要一种可复现、跨平台且无需手工清理 `pip freeze` 结果的依赖管理方式。迁移到 uv 可以以标准 `pyproject.toml` 作为声明源，以 `uv.lock` 固定完整解析结果，并为本地运行和打包提供明确命令。

## What Changes

- 在 `base_software/` 建立独立 uv 项目：
  - 新增 `pyproject.toml`，声明项目元数据、Python 要求和直接依赖。
  - 新增 `.python-version`，固定 Python `3.10.18`。
  - 新增并提交 `uv.lock`，固定跨平台依赖解析结果。
- 以源码实际导入为边界整理依赖：
  - 保留运行时使用的 Streamlit、Open3D、NumPy、Pandas、Pillow、Plotly、Kaleido、PyVista、stpyvista、Matplotlib、scikit-learn、SciPy、PyRANSAC-3D、PyLaTeX 和 tqdm。
  - 将 `pywin32` 声明为仅 Windows 安装。
  - 将 PyInstaller 放入独立的 `build` dependency group，不作为普通运行依赖。
  - 删除未使用的 TensorFlow、Keras、OpenCV、TensorBoard 及其只由原环境导出带入的依赖。
- **BREAKING** 删除 `base_software/requirements.txt`。依赖安装与执行命令统一改为 `uv sync` 和 `uv run`。
- 更新 `base_software/README.md`，说明 uv 安装、同步、运行和打包依赖组用法；不修改应用 Python 代码。
- 保留根目录 `prek` 的 Python 3.11 工具环境；uv 项目使用 Python 3.10.18，两者职责不同。

## Capabilities

### New Capabilities

无。此变更只调整开发与运行环境管理方式，不改变应用对外可见行为，因此在 `.openspec.yaml` 中设置 `skip_specs: true`，不创建 spec delta。

### Modified Capabilities

无。

## Impact

- 受影响目录：`base_software/`、`base_software/README.md`、仓库根目录现有开发说明。
- 受影响人员：Windows 本地运行者、Linux/macOS 开发者、PyInstaller 打包负责人和文档维护者。
- 不改变 Streamlit 页面、算法函数、缓存协议或报告输出。
- 新增的 `uv.lock` 会显著增加仓库变更体量，但可消除同一版本约束在不同机器上的解析漂移。
- 不使用 GitHub Actions；所有 uv 验证与锁文件更新均由维护者在本地显式执行。

## Rollback Plan

1. 从迁移前提交恢复 `base_software/requirements.txt`。
2. 删除 `base_software/pyproject.toml`、`base_software/uv.lock` 和 `base_software/.python-version`。
3. 恢复 README 中原有的 pip/requirements 安装说明。
4. 不涉及数据迁移；应用源码未改变，因此无需回滚业务逻辑或缓存文件。

## Coordination

- 维护者确认移除 `requirements.txt` 不会破坏现有本地部署流程。
- Windows 打包负责人确认 `pywin32` 与 PyInstaller dependency group 的边界。
- 文档维护者在本变更实施后同步运行 OpenWiki 本地更新，不创建 GitHub Actions。
