# AGENTS

## 行为大纲

### 编码前先思考 (Think Before Coding)

明确陈述假设；不确定的地方要提问而不是靠猜；暴露权衡，列出多种方案的优缺点；如果存在更简单的方法，要予以反驳。

### 简洁优先 (Simplicity First)

只写能解决问题的最少代码；不写投机性功能；不为单次使用的代码做抽象；如果资深工程师会觉得过度复杂——简化它。

### 外科手术式修改 (Surgical Changes)

只触碰必须修改的地方；不要顺便"优化"无关的代码、注释或格式；不重构没坏的东西；匹配现有风格。

### 目标驱动执行 (Goal-Driven Execution)

定义成功标准并循环直到验证成功；不要直接开始执行，而是定义"成功是什么样"，让再进行迭代；能用更少步骤达成就用更少步骤。

### 确定性逻辑禁止交给模型 (No Non-Language Work)

重试策略、路由逻辑、阈值判断等确定性决策必须写成显式代码（条件语句、配置值、查找表）；如果答案每次都一样，那它就不是语言任务；模型只负责分类、摘要、草稿、歧义消解。

### 硬性 Token 预算，无例外 (Hard Token Budgets)

每个迭代循环（调试、重构、生成）都必须设定预算（最大迭代次数、token 数或耗时），具体数值根据项目实际设定。预算耗尽时立即停止并展示当前结果；已被拒绝的修复方案不要再次建议。

### 暴露冲突，不要折中 (Surface Conflicts)

当代码库存在两种矛盾模式时，明确指出冲突（"模块 A 用模式 X，模块 B 用模式 Y，新代码该遵循哪个？"），等待人类决策；不要混合（Blend）两种模式，更不要自行选择。

### 先读再写 (Read Before You Write)

在添加代码前，必须阅读当前文件及其导入关系文件，检查是否已存在功能相同的函数、工具方法或常量；如果已有重复实现，直接使用，不要创建第二个版本。

### 测试必须有，但不是目的 (Tests Verify Intent)

测试要验证正确行为的有意义属性（值、结构、副作用、错误类型），而非仅验证"函数有返回值"或"不报错"；"所有测试通过"是必要条件但非充分条件；测试太弱时要明确指出。

### 长任务需要检查点 (Checkpoints)

超过 3 步或修改超过 3 个文件的任务，每步都要总结进度（做了什么＋改了什么＋当前状态）；某步失败时回滚到上一个检查点，不在错误状态上继续；失去逻辑追踪时立即停止并重述。

### 惯例优先于新颖 (Convention Beats Novelty)

即使你认为自己的写法更好，也要遵从代码库现有的命名和架构惯例（如 snake_case vs camelCase）；引入第二种模式比任何单一模式都更糟糕；认为惯例该改时，明确提出并等待批准后再行动。

### 失败必须显性化 (Fail Loud)

错误必须被抛出、返回或上报，严禁吞掉或藏在默认值背后；迁移、批处理跳过记录时，跳过数量和原因必须在输出中展示而非埋在日志里；不能 100% 确认成功时，必须明确说明，严禁默认成功。

### 提交规范与分步提交 (Commit Discipline)

- 改动前先规划实施计划：明确目标、改动步骤与验收标准，再动手。
- 分步骤、小步提交：每完成一个逻辑完整且验证通过的改动后再提交，禁止一次提交夹带无关改动。
- 提交信息遵循 Conventional Commits（`docs:` / `feat:` / `fix:` 等）。
- 只提交与当前任务相关的文件；提交前用 `git status` / `git diff` 复核暂存内容。

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tools** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them. `codegraph_node` returns one symbol's source + callers, or reads a whole file with line numbers. If the tools are listed but deferred, load them by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` and `codegraph node <symbol-or-file>` print the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

<!-- OPENWIKI:START -->

## OpenWiki

This repository has a generated `openwiki/` evidence index. It is optional just-in-time context, not required startup reading.

- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

The scheduled OpenWiki GitHub Actions workflow refreshes the repository wiki. Do not hand-edit generated OpenWiki pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate.

<!-- OPENWIKI:END -->
