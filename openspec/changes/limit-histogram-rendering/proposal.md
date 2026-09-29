# Proposal

## Why

Point2Point 在测试数据上会产生约 5347.33 mm 的偏差，当前页面直方图因此生成 5348 个柱和 1337 个 x 轴刻度；浏览器把它交给 Plotly 渲染时约需 19 秒，原标签页主线程被占住，外部表现为 API pending。Point2Plane 当前结果接近 0，直方图近似为空，因此不会触发该问题。

问题在浏览器展示复杂度，不在偏差算法、PDF 报告或 session 文件大小。需要在保留算法结果和报告一致性的前提下，限制页面直方图的渲染数量。

## What Changes

- 质量评估结果增加浏览器展示专用的 `ui_figure`，从同一次计算的偏差数据生成。
- 浏览器展示直方图固定限制为最多 256 个柱、最多 20 个 x 轴刻度；超过限制时对连续 bin 做确定性聚合，频率求和，悬停显示聚合后的区间与频数。
- 前端质量评估页面优先使用 `ui_figure`；现有 `figure` 保留，用于兼容已有结果结构和 PDF 相关逻辑。
- 前端在交给 Plotly 前必须把 Vue 响应式 figure 转换为普通 JSON 对象，避免 Plotly 遍历 Proxy 时阻塞浏览器 renderer。
- 原始偏差数组、四项统计指标、PDF 图表、PDF 命名和版式保持不变。
- 不修改 `base_software`，不改变 Point2Point/Point2Plane 的计算语义。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `dimension-quality-assessment`: 增加浏览器直方图的固定复杂度上限要求，确保大数据量偏差结果不会阻塞页面。

## Impact

- 后端预计修改 `backend/app/report/figures.py`、`backend/app/services/quality.py` 及相关测试。
- 前端预计修改 `frontend/src/views/quality/QualityAssessView.vue`、`frontend/src/components/DeviationHistogram.vue` 及相关测试。
- 任务结果 API 新增可选 `ui_figure`；现有 `figure` 保持兼容。
- 不新增运行时依赖，不迁移数据，不改变 PDF 报告内容。
- 不影响 Point2Plane、PDF 生成超时、会话工作区或上传流程。

## Rollback Plan

回滚时删除 `ui_figure` 的生成与前端读取逻辑，恢复前端直接渲染 `figure`；原算法、报告文件、统计指标和现有 API 数据不被修改，无需数据迁移。

## Coordination

- 后端负责生成受限的 UI figure，并提供与原始 figure 一致的结果数据来源。
- 前端负责使用受限 figure 渲染并保留现有悬停交互。
- 测试维护者负责覆盖大数据量 P2Point、空结果 P2Plane、柱/刻度上限和 PDF 不变性。
