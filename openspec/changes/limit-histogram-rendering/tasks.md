# Tasks

## 1. Backend UI Histogram

- [x] 1.1 在 `backend/app/report/figures.py` 增加 UI 直方图上限常量（最多 256 个柱、最多 20 个刻度）和自适应参数计算，验证合成大范围误差数据生成的 UI 参数满足上限。
- [x] 1.2 在 `backend/app/services/quality.py` 保留现有原始 `figure` 和 PDF 生成顺序，新增基于同一 `error_sorted` 与 `line` 的 `summary.ui_figure`，验证原始 `figure` 结构不变且 `ui_figure` 柱/刻度受限。
- [x] 1.3 补充 `backend/tests/test_services_quality.py`：覆盖 Point2Point 大范围数据、Point2Plane 空结果、统计指标与剔除线一致，验证 `cd backend && PATH="$HOME/.local/bin:$PATH" uv run pytest -q tests/test_services_quality.py` 通过。

## 2. Frontend Display

- [x] 2.1 在 `frontend/src/utils/qa.ts` 增加 `selectHistogramFigure(summary)`，优先返回 `ui_figure`，缺失时兼容返回 `figure`；在 `frontend/src/utils/__tests__/qa.spec.ts` 覆盖两种分支。
- [x] 2.2 更新 `frontend/src/views/quality/QualityAssessView.vue` 使用该 helper 生成页面直方图数据，验证 `cd frontend && npm run type-check` 通过。
- [x] 2.3 保留 `DeviationHistogram.vue` 的悬停和 Plotly 渲染逻辑，验证受限图仍能显示聚合区间、统计注释和剔除线。

## 3. Integration Verification

- [ ] 3.1 运行前端相关测试，验证 `cd frontend && npm run test:unit` 通过，且新的 figure 选择测试通过。
- [ ] 3.2 运行后端完整测试，验证 `cd backend && PATH="$HOME/.local/bin:$PATH" uv run pytest -q` 通过。
- [ ] 3.3 生成一次产生约 5347.33 mm 误差的 Point2Point 结果，在浏览器中确认页面完成渲染且保持响应；同时确认 `ui_figure` 不超过 256 个柱和 20 个刻度，PDF 仍使用原始报告图。
- [ ] 3.4 运行 `openspec validate limit-histogram-rendering --strict` 和 `git diff --check`，验证规划有效且不包含无关改动。
