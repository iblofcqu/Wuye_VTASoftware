# Tasks

## 1. Report Timeout Core

- [x] 1.1 在 `backend/app/config.py` 增加 `WUYE_REPORT_TIMEOUT_SECONDS`，默认 `300`，并验证正值/上下界校验和默认值。
- [x] 1.2 新增报告 supervisor/超时模块，使用独立子进程执行报告阶段，定义 `ReportTimeoutError(timeout_seconds, stage)` 和报告阶段状态文件；验证：阻塞测试 target 在短超时后返回带最后阶段的异常。
- [x] 1.3 实现跨平台进程树清理：Linux 使用独立进程组，Windows 使用 `taskkill /F /T`；验证：单元测试覆盖两个平台分支，失败清理时仍保留超时失败结果。

## 2. Report Phase Integration

- [x] 2.1 在质量评估报告阶段增加阶段标记：输入点云图、环境/检测点图、偏差云图、Plotly/Kaleido 直方图、LaTeX/PDF 编译；验证：每个阶段都会被写入 `report_state.json`，且 `progress.json` 仍兼容前端。
- [x] 2.2 将 `quality-assess` 工具路由到 supervisor；验证：正常报告仍生成 PDF，超时任务返回 failed 且不登记 report artifact。
- [x] 2.3 验证超时后 worker 被释放，队列中的下一个任务能继续执行；验证：使用短超时和排队任务的后端集成测试通过。

## 3. Tests and Regression

- [x] 3.1 增加超时、阶段提示、跨平台清理和无产物登记的 pytest 测试；验证：指定测试全部通过，且不依赖真实 Chrome/TeX 卡死。
- [x] 3.2 运行现有后端测试和真实报告工具链测试；验证：`cd backend && PATH="$HOME/.local/bin:$PATH" uv run pytest -q` 通过。
- [x] 3.3 用可注入的短超时执行一次质量评估，记录失败错误包含超时秒数和最后阶段；验证：任务状态为 failed，错误文本包含超时信息和阶段标识。

## 4. Documentation and Verification

- [x] 4.1 在 `backend/README.md` 的环境变量表和测试说明中记录 `WUYE_REPORT_TIMEOUT_SECONDS` 及超时行为；验证：Linux/Windows 用户都能从 README 找到默认值和配置方式。
- [x] 4.2 运行 `openspec validate add-report-generation-timeout --strict` 与 `git diff --check`；验证：规划结构有效且变更范围只包含本需求相关文件。
