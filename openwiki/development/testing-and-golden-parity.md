---
type: development-guide
title: 测试、Golden 基线与端到端验收
description: 说明 backend pytest、golden parity、报告超时、直方图上限、上传/任务/预览测试、frontend Vitest、lint/build 与端到端演示清单如何验证 B/S 迁移后的行为。
tags: [testing, golden, parity, pytest, vitest, e2e]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T08:08:46.977Z
sources:
  - id: openwiki-source-1d55634d256e9e48fe3ca741
    resource: repo://backend/app/core/health.py
  - id: openwiki-source-6b45f4b822f7d3826e57be75
    resource: repo://backend/docs/e2e-checklist.md
  - id: openwiki-source-52be947af5f6e3b68e3c6e5f
    resource: repo://backend/tests/e2e_demo_checklist.py
  - id: openwiki-source-f5e860cb632dd975a73af371
    resource: repo://backend/tests/golden/generate_fixtures.py
  - id: openwiki-source-a4609782da505aa28ee1da22
    resource: repo://backend/tests/test_golden_parity.py
  - id: openwiki-source-b90c8ebf4d4e394d1aa824cc
    resource: repo://backend/tests/test_jobs_failure_interrupt.py
  - id: openwiki-source-ed437f83ef97dbc72fd4755f
    resource: repo://backend/tests/test_preview_api.py
  - id: openwiki-source-5378d9b430ed01a79fe9470f
    resource: repo://backend/tests/test_report_timeout.py
  - id: openwiki-source-1261108d77ca574ba4899ab8
    resource: repo://backend/tests/test_report_toolchain.py
  - id: openwiki-source-d626fc2da0c4248b1c11029c
    resource: repo://backend/tests/test_sessions.py
  - id: openwiki-source-b91f4f7fece49159407f8f85
    resource: repo://backend/tests/test_uploads_resume_integration.py
  - id: openwiki-source-1047363cf615000e4c9bb694
    resource: repo://frontend/package.json
  - id: openwiki-source-aee8b855fcc57d56df065759
    resource: repo://frontend/src/api/__tests__/jobs.spec.ts
  - id: openwiki-source-346a50eb1552973c66fc3a45
    resource: repo://frontend/src/api/__tests__/uploaderResume.spec.ts
  - id: openwiki-source-8e9bee8aa076ddc66a8bd88f
    resource: repo://frontend/src/utils/__tests__/qa.spec.ts
  - id: openwiki-source-a95e976d37ac85bc78f2bcd3
    resource: repo://frontend/src/utils/__tests__/wypv.spec.ts
generated: { by: "codex", at: "2026-09-29T08:08:46.977Z" }
---

# 测试、Golden 基线与端到端验收

## 验证分层

当前仓库的验证不是单一测试命令，而是三层：

1. **基线一致性测试**：用 `base_software/functions` 与原页面作为参照，验证搬迁后的 `backend/app/algos` 和 `backend/app/services` 没有改变可观察行为。
2. **基础设施与 API 测试**：验证会话、产物、分片上传、任务执行、预览、报告和健康检查的边界与失败语义。
3. **端到端演示清单**：在一个临时会话中串联 7 个工具、预览、报告下载、断点续传、失败显式化和服务重启中断。

前端另有 Vitest 单测和 `type-check`/lint/build 门禁；它们验证 API 轮询、上传恢复、WYPV 解析、指标格式和 store 状态，不替代浏览器 GPU 渲染的人工/环境验证。

## Golden parity 策略

`backend/tests/golden/generate_fixtures.py` 用固定种子生成 `sample_scene.xyz`、`sample_bim.xyz` 和 `sample_mesh.ply`，作为可重复的小规模对比输入。`test_golden_parity.py` 对不同算法使用不同强度的契约：

| 类型 | 验证方式 |
| --- | --- |
| 点云读取、单位缩放、体素/均匀下采样 | 与基线逐点完全一致 |
| Poisson-disk 网格离散 | 点数必须一致；位置、质心、包围盒和平均最近邻间距使用显式容差 |
| FPFH 粗配准 | 三个相关函数源码逐字一致；再用“优于未配准基线”的质量阈值验证行为 |
| ICP | 与基线使用容差比较 |
| KDTree/Point2Point/Point2Plane | 对小样例逐点比较 |
| 已知边界 | 邻域不足记 0、空 `find_r` 抛错等行为按原样保留并断言 |

FPFH/RANSAC 是随机算法，不能把“单次坐标完全相同”作为可靠断言；测试把随机性限定在“实现未修改 + 质量契约成立”的范围内。

## 后端测试范围

`backend/tests/` 当前分为以下主题：

- `test_golden_parity.py`：算法迁移一致性。
- `test_report_timeout.py`、`report_timeout_helpers.py`：报告超时默认值/边界、最后阶段错误、进程树清理、超时后 worker 释放和无 PDF 登记。
- `test_services_*`：离散、缩放、下采样、FPFH、ICP 和质量评估服务的输出命名、数值和非法参数。
- `test_sessions.py`、`test_artifacts.py`：会话持久化、并发写保护、产物登记、下载命名、跨会话隔离和路径穿越拒绝。
- `test_uploads_*`：分片幂等、哈希/长度校验、取消、TTL、完成后的整体校验和中断后续传。
- `test_jobs_*`：任务生命周期、池容量排队、阶段进度、失败显式化、无产物失败和服务重启中断。
- `test_preview_core.py`、`test_preview_api.py`：WYPV 编码、点数上限、缓存、标量对齐、偏差云置零和 API 失败边界。
- `test_health.py`：TeX、Chromium、离屏渲染和字体自检结构及失败上报。
- `test_report_module.py`、`test_report_toolchain.py`：报告图片/LaTeX 源生成、无 Streamlit 依赖和真实 PDF 编译。
- `test_services_quality.py`：质量评估正常路径、Point2Plane 空结果、`ui_figure` 柱/刻度上限和统计/剔除线一致性。

本次验证运行：

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest -q
```

结果为 `134 passed`，并在真实报告链路测试中生成 PDF；测试同时报告 FastAPI/Starlette、Matplotlib 和 Kaleido 的弃用警告，这些是依赖升级提示，不是当前断言失败。

## 前端测试范围

`frontend/src/**/__tests__/` 覆盖：

- `pollJob`：成功、失败终态和 abort 后停止轮询。
- `uploadFile`：分片上传、多文件独立失败、并发限制、非安全上下文 SHA-256、回退后的断点恢复和重试。
- workspace store：会话快照加载、产物查询和错误状态。
- WYPV：坐标与标量解析、非法数据拒绝；颜色模块验证命名色、十六进制和 seismic 端点。
- QA 工具：四项指标格式化、报告产物提取、`ui_figure` 选择，以及 Vue 响应式 figure 到普通 JSON 的 Plotly 边界测试。

静态与构建门禁为：

```bash
cd frontend
npm run test:unit
npm run lint
npm run build
```

当前单测为 6 个测试文件、22 个用例；`npm run test:unit`、`npm run type-check` 和生产构建均通过。构建仍会报告大 chunk 警告，但不会导致构建失败。

## 端到端演示清单

`backend/tests/e2e_demo_checklist.py` 使用临时数据目录创建应用，按顺序执行：

- `/api/health` 依赖自检。
- 中断后查询缺失分片并补齐的断点续传。
- ① 网格离散，并请求 WYPV 预览。
- ② 尺寸缩放 m→mm→m。
- ③ 体素/均匀下采样。
- ④ FPFH 粗配准。
- ⑤ ICP 精配准。
- ⑥ 质量评估、指标/直方图、报告命名。
- ⑦ PDF 下载和偏差云预览。
- 非法参数导致 failed 且错误文本可见。
- 新建应用模拟服务重启，遗留 running 任务变为 interrupted。

运行命令：

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run python tests/e2e_demo_checklist.py
```

`backend/docs/e2e-checklist.md` 记录的最近一次本机结果是 16/16 通过；该清单依赖 TeX、Chromium、离屏渲染和字体，正式演示前应按当前环境重新运行并保留真实输出。

## 当前测试盲区

- 端到端清单和 pytest 主要验证 API 与数值结果；完整 vtk.js 三维交互、鼠标旋转/缩放和 WebGL2 环境需要浏览器实机或 headless Chrome 验证。
- 真实 PDF 测试在缺少 `latexmk`/`xelatex` 时会跳过；部署环境必须依赖 `/api/health` 显式报告缺项。
- `Point2Plane` 已加入近共线/退化平面的 0 值回退和质心投影修复，但自动测试主要覆盖正常样本与稀疏邻域；更多极端共线几何组合仍可作为后续回归补充。
- 测试通过不等于算法在所有输入上都正确；质量评估的数值依赖输入尺度、单位、点密度和配准质量。

## 相关页面

- [点云处理算法与基线约束](../algorithms/point-cloud-processing.md)
- [点云预处理 B/S 工作流](../workflows/point-cloud-preprocessing.md)
- [尺寸质量评估 B/S 工作流](../workflows/dimension-quality-assessment.md)
- [开发、提交与质量门禁](quality-workflow.md)
- [B/S 运行、依赖与部署](../operations/runtime-and-deployment.md)
