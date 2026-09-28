# 贡献指南

## 项目结构（Monorepo）

本项目采用 **Monorepo** 方式组织代码，所有子模块以分目录形式存放在当前仓库根目录下.

---

## 安装 Git Commit 插件（Pre-commit Hook）

在根目录执行以下命令，安装 Git 提交规范插件：

```bash
prek install
```

> **注意**：每位开发者在克隆仓库后，首次提交前必须执行此步骤，否则 commit 校验将不会生效。

---

## 分支管理

- `main` — 主分支，保持稳定可发布状态
- `develop` — 开发分支，日常开发合并目标
- `feature/<功能名>` — 功能分支，从 `develop` 拉出
- `fix/<问题描述>` — 修复分支
- `release/<版本号>` — 发布分支

### 分支命名规范

- 功能分支：`feature/xxx`，如 `feature/hoisting-plan`
- 修复分支：`fix/xxx`，如 `fix/lift-calc-error`
- 发布分支：`release/v1.0.0`

> **注意**: 默认仅通过PR 朝中央仓库推送代码

---

## OpenWiki 文档维护

本仓库为私有仓库，未配置、也不依赖 GitHub Actions 定时更新 OpenWiki 文档：

- 不要创建或恢复 `.github/workflows/openwiki-update.yml`。
- 不要为 OpenWiki 更新配置 `OPENAI_API_KEY`、`OPENWIKI_LANGSMITH_API_KEY` 等 Actions secrets。
- OpenWiki 初始化或更新由维护者在本地显式执行，生成结果按普通文档变更进行审查和提交。
