# Proposal

## Why

现场测试中 PDF 报告生成会偶发性卡住 10 分钟以上且没有结果。当前报告链路包含 PyVista 离屏渲染、Plotly/Kaleido 浏览器导出和 `latexmk`/`xelatex` 编译，这些环节都可能因为 Windows 图形上下文、Chrome 启动或 MiKTeX/字体等待而阻塞；现有实现没有阶段级超时，卡住的 worker 还会占用计算进程池，导致后续任务排队。

## What Changes

- 为质量评估的报告生成阶段增加默认 5 分钟的超时控制，可通过 `WUYE_REPORT_TIMEOUT_SECONDS` 覆盖，默认值为 `300`。
- 超时范围覆盖报告相关的 PyVista 截图、Kaleido 直方图导出和 LaTeX/PDF 编译；不把上游点云算法计算本身纳入该超时。
- 使用独立 supervisor 子进程执行报告阶段；超时后终止整个子进程树，兼容 Linux 和 Windows 的进程树清理语义。
- 任务进入失败状态并返回明确错误，错误中包含超时秒数和最后执行的报告子阶段，例如“编译 PDF（latexmk/xelatex）”。
- 超时任务不得登记 PDF 报告 artifact；超时释放 worker，使后续排队任务可以继续。
- 增加可注入短超时的测试，覆盖正常完成、报告阶段超时、子进程清理和错误阶段提示。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `dimension-quality-assessment`: 增加报告生成超时、阶段化超时原因和超时后释放计算资源的行为要求。

## Impact

- 受影响代码预计包括 `backend/app/config.py`、`backend/app/services/quality.py`、`backend/app/jobs/runner.py` 或新增的报告 supervisor/timeout 模块、`backend/app/jobs/tools.py` 以及相关测试。
- 不改变点云算法、偏差计算、报告版式、Linux 部署路径或现有成功报告的命名规则。
- 默认行为会增加“超过 5 分钟的报告任务失败”这一边界；正常报告完成时间不变。
- Windows 和非 Windows 环境都需要处理子进程终止和清理，避免 Chrome、latexmk、xelatex 等残留进程继续占用资源。

## Rollback Plan

回滚时删除报告超时 supervisor 和 `WUYE_REPORT_TIMEOUT_SECONDS` 读取逻辑，恢复报告直接调用链；不涉及数据迁移、持久化格式或 API 兼容性回滚。

## Coordination

- 由后端实现者负责 supervisor、配置项和跨平台进程树清理。
- 由测试维护者提供可注入的阻塞场景，避免测试依赖真实 Chrome/TeX 的卡死行为。
- Windows 环境需要在实际报告链路上验证超时错误和残留进程清理；Linux 环境至少运行现有 pytest 与报告工具链测试。
