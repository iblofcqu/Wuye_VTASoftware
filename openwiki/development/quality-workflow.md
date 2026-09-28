---
type: development-guide
title: 开发与质量流程
description: 说明仓库采用的 Monorepo、分支与提交约定、prek 静态检查、OpenWiki 手动维护方式，以及当前代码行为验证不足带来的风险。
tags: [development, quality, prek, conventions]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-28T07:42:19.658Z
sources:
  - id: openwiki-source-209973db3ad81fc8590dae4c
    resource: repo://.markdownlint-cli2.yaml
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-8037e2358a2c4f9b2c722a11
    resource: repo://AGENTS.md
  - id: openwiki-source-f317ee207e1653d2033c81a4
    resource: repo://CONTRIBUTING.md
generated: { by: "codex", at: "2026-09-28T07:42:19.658Z" }
---

# 开发与质量流程

## 仓库协作约定

`CONTRIBUTING.md` 将仓库定义为 Monorepo：子项目通过根目录下的独立目录组织，当前演示应用位于 `base_software/`，工作区还预留了 `docs/`。贡献者克隆仓库后应先运行：

```bash
prek install
```

贡献指南声明的分支模型为 `main`、`develop`、`feature/<功能名>`、`fix/<问题描述>` 和 `release/<版本号>`，并说明默认仅通过 PR 向中央仓库推送。代码仓库当前只有 `main` 等实际分支时，这些名称仍是流程约定而不是自动创建或校验规则。

`AGENTS.md` 对改动过程提出更细的约束：先规划，再做外科手术式修改；一个提交只包含一个逻辑完整改动；提交信息使用 Conventional Commits；提交前用 `git status` 和 `git diff` 复核。

## prek 门禁

根目录 `.pre-commit-config.yaml` 使用 Python 3.11，并安装 `pre-commit`、`commit-msg` 和 `pre-push` 类型钩子。当前实际配置包括：

- 删除行尾空白、补齐文件末尾换行、统一 LF。
- 检查合并冲突、大小写冲突和可执行文件 shebang。
- 校验 YAML、JSON、TOML。
- 拒绝超过 1 MiB 的新增大文件。
- 通过 gitleaks 扫描硬编码密钥。
- 通过 codespell 检查英文拼写。
- 通过 markdownlint-cli2 检查 Markdown。
- 在 `commit-msg` 阶段校验 Conventional Commit。

这些钩子能阻止格式、文档、密钥和提交信息类问题，但配置中没有单元测试、集成测试、算法回归、Streamlit 页面测试或端到端测试执行器。当前仓库也未跟踪测试文件或测试运行配置，因此“`prek run --all-files` 通过”只能证明静态门禁通过，不能证明配准、偏差计算或报告生成正确。

## OpenWiki 手动维护

本仓库是私有仓库，没有配置 GitHub Actions，也不依赖定时工作流维护 OpenWiki：

- 不创建、不恢复 `.github/workflows/openwiki-update.yml`。
- 不为 OpenWiki 更新配置 Actions secrets。
- OpenWiki 初始化或更新只由维护者在本地显式执行；生成页和 Claims 按普通文档改动一起审查、提交。
- 自动化调度不能作为文档可靠性的前提，缺少定时更新不表示文档流程失效。

## Markdown 与生成页

Markdown 检查默认启用，但关闭了中文长行限制、重复标题限制、行内 HTML 限制和强制一级标题限制。OpenSpec 生成的 skill 文件以及整个 `openwiki/**` 被排除在检查之外，因为它们是生成物，手工调整格式会在下次生成时冲突。

Markdownlint 的 `fix` 设置为 `false`，规则问题需要作者确认后修复，而不是钩子自动重写。OpenWiki 也已声明生成页由工具维护；除非明确要求修复生成结果，否则应修改源码或普通文档后让 OpenWiki 重新生成。

## 验证策略的含义

由于缺少自动化行为测试，当前最可靠的验证方式仍是：

- 对修改的纯函数提供小规模、可重复的 NumPy 输入，并检查数值范围、索引、输出形状和错误语义。
- 对页面工作流使用最小点云样例，覆盖选择路径、参数转换、中间输出和报告截图。
- 明确保存失败输出，不以“页面没有抛异常”代替对坐标、点数和报告文件内容的检查。
- 在提交前运行 `prek run --all-files`，但不要把它描述为业务功能测试。
