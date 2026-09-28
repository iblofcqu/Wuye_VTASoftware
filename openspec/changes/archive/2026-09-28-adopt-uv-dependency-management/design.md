# Design

## Context

参见 `proposal.md - Why`。当前唯一依赖清单是 `base_software/requirements.txt`，内容来自完整环境导出。应用由多个 Python 脚本直接导入 Open3D、Streamlit、PyVista 等库，但没有 `pyproject.toml`、锁文件、测试套件或独立启动脚本。

已通过临时 uv 项目验证：以源码直接导入为边界、Python 3.10 为解析环境时，uv 0.11.26 可以解析 109 个包并生成锁文件。精确锁定 `open3d 0.16.0` 后可获得 Linux/Windows wheel，并选择 `numpy 2.2.6` 和 Windows 条件下的 `pywin32 311`。

## Goals / Non-Goals

**Goals:**

- 让 `base_software/` 成为一个可用 uv 独立管理的应用项目。
- 用 `pyproject.toml` 表达直接依赖、Python 范围和平台条件。
- 用提交到仓库的 `uv.lock` 固定完整解析结果。
- 让新环境只需 `uv sync --frozen` 和 `uv run` 即可复现。
- 删除失效的环境导出条目，同时不改变应用代码行为。

**Non-Goals:**

- 不升级 Streamlit、Open3D、NumPy 等主要版本。
- 不修复应用算法、缓存协议、PDF 报告或 Streamlit 页面行为。
- 不增加 GitHub Actions、CI 托管或自动锁文件更新。
- 不建立 monorepo 根级 uv workspace；其他子项目以后可按同一模式独立迁移。
- 不补齐 `.xls` 读取所需的 `xlrd` 等历史遗留可选依赖；该问题单独评估。

## Decisions

### 1. uv 项目放在 `base_software/`

选择：在 `base_software/pyproject.toml`、`base_software/uv.lock` 和 `base_software/.python-version` 管理应用，而不是放在仓库根目录。

理由：`base_software` 是当前唯一可运行子项目，目录内已有自己的 README、源码和依赖清单。独立项目可以避免根目录 Monorepo 配置绑死单个应用。

备选方案：根级 workspace。当前没有第二个 Python 项目，提前建立 workspace 会增加配置而没有收益。

### 2. Python 固定为 3.10.18

选择：`requires-python = ">=3.10.18,<3.11"`，提交 `.python-version` 内容 `3.10.18`。

理由：原环境清单明确声明 Python 3.10.18，且 Open3D 0.16 属于较旧版本，保持当前运行时基线风险最低。根目录 `prek` 使用 Python 3.11 运行检查工具，不需要与应用的运行解释器相同。

备选方案：直接升级到 Python 3.11 或更高。那会同时改变 Open3D、SciPy、PyVista 等二进制包的可选版本，超出依赖管理迁移范围。

### 3. `pyproject.toml` 取代 `requirements.txt`

选择：删除原 `requirements.txt`，不保留生成式副本；需要给外部系统临时导出时使用 `uv export`。

理由：单一依赖源可以避免 pip 与 uv 漂移。原文件约 107 行，主要记录传递依赖和环境组件，并不适合作为人工维护清单。

备选方案：保留 requirements 并额外增加 uv 文件。该方案会让两套清单同时演变，因此拒绝。

### 4. 只声明直接运行时依赖，版本范围保持兼容

计划在 `[project].dependencies` 声明：

```toml
"kaleido~=1.0.0",
"matplotlib~=3.10.3",
"numpy~=2.2.6",
"open3d==0.16.0",
"pandas~=2.3.1",
"pillow~=11.3.0",
"plotly~=6.2.0",
"pylatex~=1.4.2",
"pyransac3d~=0.6.0",
"pyvista~=0.45.3",
"scikit-learn~=1.7.1",
"scipy~=1.15.3",
"streamlit~=1.47.0",
"stpyvista~=0.1.4",
"tqdm~=4.67.1",
'pywin32==311; sys_platform == "win32"',
```

PyInstaller 放入 `[dependency-groups].build`。`[tool.uv].package = false`，因为这个 demo 不是可安装 Python 包。

理由：依赖直接对应当前 Python 文件的导入；传递依赖由 lock 管理。Open3D 精确锁定为 0.16.0，因为 PyPI 上的 0.16.1 只有 macOS wheel，而 0.16.0 仍提供 Linux 与 Windows wheel；其余依赖保留原约束，避免迁移顺带升级库。

备选方案：把 107 条环境导出全部放进 dependencies。该方案会继续保留下载体积大且未使用的 TensorFlow/Keras/OpenCV，并把传递依赖误当成直接责任。

### 5. 默认使用 Aliyun PyPI 镜像

选择：在 `pyproject.toml` 中配置：

```toml
[[tool.uv.index]]
name = "aliyun"
url = "https://mirrors.aliyun.com/pypi/simple"
default = true
```

理由：项目实际运行环境位于中国大陆，官方 PyPI 与 files.pythonhosted.org 下载大型 VTK/Open3D wheel 速度很慢。实测 Aliyun 镜像的 Open3D wheel 下载速度约 7 MB/s；镜像仍提供与 PyPI 相同的 wheel 和哈希。

备选方案：只在单次命令中传 `--default-index`。该方式无法让后续维护者直接复用同一环境策略，因此改为提交到项目配置。需要访问官方 PyPI 时，可用命令行 `--default-index` 临时覆盖。

### 6. 文档使用 uv 命令作为唯一入口

计划把 `base_software/README.md` 的命令改为：

```bash
cd base_software
uv sync --frozen
uv run streamlit run home_page.py
```

打包环境使用：

```bash
uv sync --frozen --group build
```

理由：`uv run` 自动使用项目虚拟环境，避免要求用户手工激活 `.venv`。

备选方案：继续记录 `pip install -r` 和 `python -m`。它们将与新的 lock 机制脱节。

## Affected Files

- 新增：`base_software/pyproject.toml`。
- 新增：`base_software/.python-version`。
- 新增：`base_software/uv.lock`。
- 删除：`base_software/requirements.txt`。
- 更新：`base_software/README.md` 的安装与运行说明。
- 更新：根目录 `.gitignore`，忽略项目内 `.venv/`。
- 不修改：`base_software/*.py`、`base_software/functions/*.py`、`base_software/pages/*.py`。
- 后续文档同步：OpenWiki 由维护者本地更新，不创建 GitHub Actions。
- 默认索引配置：`base_software/pyproject.toml` 中的 `[[tool.uv.index]]`。

## Risks / Trade-offs

- [Open3D 0.16.0 与 NumPy 2.2.x 可能在运行时导入失败] → 锁文件生成后必须执行真实 import smoke test；失败时停止实施并单独请求版本调整决策，不使用无约束升级掩盖问题。
- [删除 requirements 会打断既有 pip 工作流] → 在 README 中提供 uv 迁移命令，并在提交信息中标记破坏性变更。
- [锁文件跨平台体积较大] → 提交 `uv.lock`，但只将依赖组用于必要命令；不额外复制导出文件。
- [Windows marker 配置错误会导致 Linux/macOS 安装 pywin32] → 用 PEP 508 marker `sys_platform == "win32"`，并在 Linux 上执行 `uv sync` 验证不会选择 Windows 包。
- [精简依赖可能遗漏隐藏的运行时导入] → 以 `rg` 导入清单和 uv import smoke test 验证；若发现漏项，只补充实际直接依赖，不重新复制完整 freeze。
- [没有自动化测试，uv sync 成功不能证明应用可运行] → 将验证限于锁文件、环境同步、模块导入和 Streamlit 启动检查，并在总结中明确未覆盖的算法行为。
- [锁文件带来供应链与安全边界变化] → 使用受控的 Aliyun PyPI 镜像和 lock 中的哈希，执行 `uv sync --frozen`；不添加额外私有索引或脚本。

## Migration Plan

1. 创建 `pyproject.toml`、`.python-version`，生成并检查 `uv.lock`。
2. 在临时或本地 uv 环境中执行锁定、同步和 import smoke test。
3. 更新 README 的安装、运行和打包说明。
4. 删除 `requirements.txt`。
5. 运行 `prek run --all-files`。
6. 若任一步失败，保留原 requirements，不提交半迁移状态；已完成部分按 proposal 的回滚步骤撤销。

## Open Questions

无。会影响范围或验收的版本策略已在上述决策中固定；Open3D/NumPy 的运行时兼容性将在实施阶段作为显式门禁验证。
