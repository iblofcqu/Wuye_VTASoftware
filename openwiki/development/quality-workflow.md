---
type: development-guide
title: 开发、提交与质量门禁
description: 说明 monorepo 协作约定、Conventional Commits、prek/pre-commit 静态门禁、OpenSpec 变更流程、后端/前端测试入口，以及 OpenWiki 只在本地手动维护的边界。
tags: [development, quality, prek, openspec, openwiki]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-209973db3ad81fc8590dae4c
    resource: repo://.markdownlint-cli2.yaml
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-8037e2358a2c4f9b2c722a11
    resource: repo://AGENTS.md
  - id: openwiki-source-6b45f4b822f7d3826e57be75
    resource: repo://backend/docs/e2e-checklist.md
  - id: openwiki-source-070c6307b3860e1806baf566
    resource: repo://backend/pyproject.toml
  - id: openwiki-source-f317ee207e1653d2033c81a4
    resource: repo://CONTRIBUTING.md
  - id: openwiki-source-1047363cf615000e4c9bb694
    resource: repo://frontend/package.json
  - id: openwiki-source-38af7bdd34d817fbd3c29077
    resource: repo://openspec/config.yaml
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 开发、提交与质量门禁

## 仓库协作约定

`CONTRIBUTING.md` 把仓库定义为 Monorepo：子模块放在仓库根目录下的独立目录；当前主实现是 `frontend/` 与 `backend/`，`base_software/` 是历史基线，`docs/` 存放说明书与原始 demo 文档。

贡献者在克隆仓库后应执行：

```bash
prek install
```

贡献指南声明的分支模型为 `main`、`develop`、`feature/<功能名>`、`fix/<问题描述>` 和 `release/<版本号>`，并预期通过 PR 向中央仓库推送。实际仓库分支和远端策略仍需以维护者配置为准。

`AGENTS.md` 进一步要求：改动前规划，一次提交只包含一个逻辑完整改动，提交信息使用 Conventional Commits，提交前检查 `git status` 和 `git diff`。这些约定适用于源码、测试、OpenSpec 和 OpenWiki 文档改动。

## prek / pre-commit 门禁

根目录 `.pre-commit-config.yaml` 使用 Python 3.11，并安装 `pre-commit`、`commit-msg`、`pre-push` 类型钩子。当前实际检查包括：

- 删除行尾空白、补齐文件末尾换行、统一 LF。
- 检查合并冲突、大小写冲突、可执行文件 shebang。
- 校验 YAML、JSON、TOML。
- 拒绝超过 1 MiB 的新增大文件。
- 通过 gitleaks 扫描硬编码密钥。
- 通过 codespell 检查英文拼写。
- 通过 markdownlint-cli2 检查 Markdown。
- 在 `commit-msg` 阶段校验 Conventional Commit。

两个与 B/S 迁移相关的排除规则需要保留：

- `check-json` 排除 `tsconfig*.json`，因为前端 tsconfig 使用 JSONC；其语法由 `tsc`/`vue-tsc` 验证。
- `codespell` 排除 `package-lock.json`，避免生成文件中的完整性哈希产生误报。

pre-commit 配置本身仍只执行静态检查，不直接运行单元、集成或端到端测试；但测试已经存在于源码树中，提交前应按改动范围运行它们，不能把 `prek run --all-files` 等同于业务验证。

## 当前测试入口

仓库现在已经包含明确的测试层：

- `cd backend && uv run pytest -q`：后端 pytest，覆盖算法 golden parity、会话、上传、任务、预览、报告和健康检查。
- `cd backend && PATH="$HOME/.local/bin:$PATH" uv run pytest -q`：在 TinyTeX 等用户级依赖已安装时包含真实 PDF 报告链路。
- `cd backend && PATH="$HOME/.local/bin:$PATH" uv run python tests/e2e_demo_checklist.py`：7 个工具、报告、断点续传、失败显式化和重启中断的端到端清单。
- `cd frontend && npm run test:unit`：Vitest 单测。
- `cd frontend && npm run lint && npm run build`：前端静态检查、类型检查和生产构建。

具体测试属性、golden 容差和最近一次回归记录见[测试、Golden 基线与端到端验收](testing-and-golden-parity.md)。

## OpenSpec 工作流

`openspec/` 保存能力规范、变更计划和归档记录。`openspec/config.yaml` 为 proposal、specs、design 和 tasks 定义项目级规则，例如：

- 提案必须包含回滚计划、影响面和协调项。
- specs 使用 Given/When/Then，优先引用现有模式并包含边界条件。
- design 说明决策理由、受影响模块以及性能/安全影响。
- tasks 按模块分组、粒度细，并包含必要测试。

归档操作还有独立 guidance：移动 change 目录后立即创建只包含归档移动、同步主 specs 和必要配置的提交，提交信息使用 `docs(openspec): archive <change-name>`。当前 `migrate-demo-to-bs-architecture` 已经同步到 `openspec/specs/` 并归档到 `openspec/changes/archive/`。

## OpenWiki 手动维护

本仓库是私有仓库，没有配置 GitHub Actions，也不依赖定时工作流维护 OpenWiki：

- 不创建或恢复 `.github/workflows/openwiki-update.yml`。
- 不为 OpenWiki 更新配置 Actions secrets。
- OpenWiki 初始化或更新只由维护者在本地显式执行；生成页和 Claims 作为普通文档改动审查和提交。
- 不直接手改生成页；优先修改源码、测试和普通文档后重新生成。

需要明确一个仓库内文档冲突：`CONTRIBUTING.md` 和 `openwiki/INSTRUCTIONS.md` 禁止依赖定时工作流，但 `AGENTS.md` 末尾仍保留“scheduled OpenWiki GitHub Actions workflow”的旧句子。当前有效约定应以贡献指南和 OpenWiki 仓库说明为准；在源码未修正前，维护者不应据此创建或恢复 Actions 工作流。

## Markdown 与生成页

`.markdownlint-cli2.yaml` 默认启用规则，但关闭了中文长行限制、重复标题限制、行内 HTML 限制和强制一级标题限制。它忽略 `.agents/skills/openspec-*/SKILL.md` 和整个 `openwiki/**`，因为这些是生成物；自动修复也设为 `false`，规则问题应由作者确认后修复。

OpenWiki 生成页使用 OKF frontmatter 加正文 H1，因此不在普通仓库 Markdown 规则内。生成页的更新方式是通过 OpenWiki 生命周期重新生成，而不是手工调整格式。

## 相关页面

- [测试、Golden 基线与端到端验收](testing-and-golden-parity.md)
- [仓库与应用架构总览](../architecture/application-overview.md)
- [B/S 运行、依赖与部署](../operations/runtime-and-deployment.md)
- [快速开始](../quickstart.md)
