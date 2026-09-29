# 端到端演示清单（B/S 版本）

用于演示/验收前的一次性全流程核对，覆盖 7 个工具、PDF 报告、断点续传、失败显式化与服务重启中断。

## 运行

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run python tests/e2e_demo_checklist.py
```

前置条件：`curl http://<host>:<port>/api/health` 为 `ok`（TeX/Chromium/离屏渲染/中文字体齐全）。

## 清单项（脚本逐项输出 PASS/FAIL）

| # | 场景 | 判定 |
| --- | --- | --- |
| 0 | 依赖自检 `/api/health` | status == ok |
| 1 | 断点续传（上传中途查询缺失分片后补齐） | 产物登记成功 |
| 2 | ① 网格离散 | `<网格名>.xyz`，可预览（WYPV） |
| 3 | ② 尺寸缩放 m→mm→m | `_mm.xyz` / `_m.xyz`，单位链路一致 |
| 4 | ③ 体素下采样 / 均匀下采样 | `_VD.xyz` / `_UD.xyz` |
| 5 | ④ FPFH 粗配准 | `_FPFH.xyz` |
| 6 | ⑤ ICP 精配准 | `_ICP.xyz` |
| 7 | ⑥ 质量评估 | 指标（check_num>0）+ 直方图 figure + 偏差云预览 |
| 8 | ⑥ 报告命名与下载 | 报告名含"几何质量评估报告"+日期；下载为合法 PDF |
| 9 | 失败显式化 | 非法参数 → failed + 明确原因 |
| 10 | 重启中断 | 遗留 running 任务 → interrupted（服务重启导致任务中断） |

## 最近一次记录（2026-09-29，本机 Linux）

- 脚本结果：**16/16 项通过**（报告约 280–300 KB，偏差云预览 WYPV）。
- UI 页面渲染（headless Chrome 截图核对）：首页（品牌图/标题/侧边导航与原 demo 一致）、网格离散页、质量评估页（四个前置确认 + 门禁提示）均正常。
- UI 数据态（3D 视图旋转缩放、直方图悬停）已通过组件单测（WYPV 解析/色带/指标口径）与 API 级端到端覆盖；
  建议正式演示前按使用说明手册做一次人工点击走查（上传→任务→预览→下载）。

## 全量回归记录（2026-09-29）

| 回归项 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `cd backend && PATH="$HOME/.local/bin:$PATH" uv run pytest -q` | 121 passed |
| 端到端演示清单 | `cd backend && PATH="$HOME/.local/bin:$PATH" uv run python tests/e2e_demo_checklist.py` | 16/16 通过 |
| 前端单测 | `cd frontend && npm run test:unit` | 17 passed（6 文件） |
| 前端静态检查 | `cd frontend && npm run lint` | 通过 |
| 前端构建 | `cd frontend && npm run build` | 通过 |
