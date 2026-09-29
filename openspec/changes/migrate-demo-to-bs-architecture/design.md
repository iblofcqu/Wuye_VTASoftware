# Design

## Context

- `base_software/` 是 Streamlit 单进程演示：页面直接执行重计算，文件选择依赖服务器端 tkinter 对话框，跨步骤状态是 `cache/*.txt` 路径协议，结果交付依赖 `os.startfile`。局域网用户无法选择自己电脑上的文件，也无法感知进度与失败。
- 已确认的约束：五冶以按钮跳转到独立 Web 页；无登录；UI 与原 demo 一致；算法行为严格保持原样；演示级规模，但 Web 进程与计算进程必须分离；Linux 裸机 + uv 部署；会话工作区用 JSON 清单（不引入 Redis/SQLite）；大文件上传必须支持断点续传；点云预览必须轻量化后再呈现。
- 可复用资产：`base_software/functions/` 中纯 NumPy/Open3D 算法；报告链路（pyvista 离屏截图 + Plotly/kaleido 出图 + pylatex/ctex 编译）需要保留。
- 行为契约见 `specs/`（7 个能力）；动机见 `proposal.md`。

## Goals / Non-Goals

### Goals

- 浏览器内完成全部文件交互：上传（含断点续传）、下载、预览、进度与失败可见。
- 算法零行为改动搬迁，数值一致性可用 golden 测试证明。
- Web 进程始终可响应；重计算在独立计算进程池执行。
- 会话内产物复用替代 `cache/*.txt` 路径协议；不同会话互不干扰。
- 单命令启动（Linux + uv），依赖安装有清单、启动自检可验证。

### Non-Goals

- 不做登录/权限、多租户、水平扩展、高可用。
- 不引入 Redis、SQLite、Celery 或消息队列。
- 不做 Docker 镜像（留待后续独立变更）。
- 不引入 SSE/WebSocket（任务进度用轮询）。
- 不修复算法已知缺陷，不改变文件命名、格式与报告版式。

## Decisions

### D1 架构：FastAPI Web 单实例 + 计算进程池

- 选择：一个 FastAPI Web 进程负责 API、会话、静态资源与任务调度；重计算全部提交给 `ProcessPoolExecutor`（spawn）执行，池容量可配置（默认 2）。
- 理由：算法必须是 Python；Web 与计算分离保证长任务期间页面与进度查询始终可响应；单 Web 实例使会话状态天然一致（演示无横向扩展需求）。
- 备选与否决：多 uvicorn worker 需要共享会话存储（Redis 或外部存储）→ 超出演示范围；Celery + Redis 增加了运维组件 → 否决；线程池会被 GIL 与长任务拖累 → 否决。

### D2 任务模型：状态机 + 进度回传 + 轮询

- 选择：任务状态 `queued → running → succeeded / failed / interrupted`；worker 通过 `multiprocessing.Queue` 回传阶段进度，Web 进程写入会话清单；前端每 1 秒轮询 `GET /api/jobs/{id}`。
- 理由：与 specs 的分步进度、失败显式、重启中断语义直接对应；轮询实现与排障成本最低。
- 备选与否决：SSE/WebSocket 实时性更好但演示无需求，后续如需可独立升级；同步执行违反"Web 保持响应"要求 → 否决。
- 边界：服务启动时把清单中遗留的 `running/queued` 任务置为 `interrupted` 并写入原因；池满时任务停留在 `queued`。

### D3 数值一致性：同版本依赖 + 原样搬运 + golden 测试

- 选择：`backend/app/algos/` 从 `base_software/functions/` 原样复制（仅调整 import、剥离 streamlit/stpyvista 耦合），不重命名、不重构、不修缺陷；后端 Python 3.10.18、open3d==0.16.0 与基线一致；**numpy 例外：固定 `~=1.26.4`**——实测 open3d 0.16 与 numpy 2.x ABI 不兼容，registration/ICP 路径直接 segfault，numpy 1.26.4 下 ICP/RANSAC 实测正常。
- 理由：同代码 + 同算法库版本是"同输入同输出"的最强保证；numpy 只影响数组桥接层；golden 测试提供可验证证据（ICP/FPFH 已实测逐点一致）。
- 备选与否决：借搬迁顺手重构（会让数值差异难以归因）→ 否决；升级 open3d 到 ≥0.19（支持 numpy 2）会改变算法实现 → 与"严格保持原样"冲突，否决；保留 numpy 2 的 workaround 不可靠（RANSAC 等路径同样崩溃）→ 否决。
- 细节：`services/` 只做用例编排（参数校验、输入输出路径、进度回调）；golden 测试用合成小样例对比基线函数与新实现（容差 0 或显式声明）。

### D4 会话与存储：单实例 + 会话 JSON + 产物 id 存储

- 选择：`data/sessions/<session_id>/session.json` 作为唯一真源（原子替换写）；产物文件内部按 artifact id 存储，下载时还原原演示命名；首次请求下发持久 cookie（HttpOnly、SameSite=Lax、默认 30 天可配）。
- 理由：无数据库即可满足隔离、复用与重启恢复；JSON 便于排障；id 存储避免同名覆盖，同时保住用户可见命名。
- 备选与否决：SQLite 更规范但用户明确不需要；Redis 引入外部服务 → 否决。
- 细节：单 Web 实例 + 进程内锁保证写一致性；`session.json` 记录产物、任务、未完成上传三类条目。

### D5 断点续传：分片 + 幂等分片提交 + 完整性校验

- 选择：分片上传（默认 8MB，可配），分片按索引幂等提交；每个分片携带 SHA-256；`complete` 时做整体一致性校验后才登记产物；未完成上传默认保留 24h（可配）后清理。
- 理由：网络中断只补缺失分片；幂等提交让重试天然安全；分片级校验能精确重传损坏部分。
- 备选与否决：流式 + offset 续传可行，但断点重试语义更复杂；整文件单请求无法满足"网络不稳定"要求 → 否决。
- 前端配合：`File.slice()` 切分；逐片 SHA-256（Web Crypto，8MB 分片开销小）；失败指数退避重试，默认并发 2 个分片；localStorage 保存 `upload_id` 与文件指纹（名称+大小+修改时间）。
- 明确限制：页面刷新/重开后浏览器丢失 File 句柄，需要用户重新选择同一文件后从缺失分片继续（不重传已完成部分）；网络闪断在页面未刷新时自动续传。

### D6 预览管线：服务端轻量化 + 二进制传输 + 前端渲染

- 选择：任务成功后由服务端生成预览数据集（默认目标 ≤100 万点，可配），缓存到会话目录；以"JSON 头 + Float32 坐标 + 可选标量/颜色"的二进制格式提供；前端用 vtk.js 渲染。
- 理由：全量点云不进浏览器；保持旋转/缩放/平移与红蓝双云、误差色带的交互语义；计算始终使用全量数据。
- 备选与否决：服务端渲染图片（丢失交互，违背原操作习惯）→ 否决；全量传输（大文件不可行）→ 否决。

### D7 报告链路：保留原实现与依赖

- 选择：保留 pyvista 离屏截图（报告用图）、Plotly + kaleido（直方图图片）、pylatex + ctex（PDF 编译），环节、命名与版式不变；`/api/health` 启动自检 latexmk/xelatex、chromium、离屏渲染与中文字体，缺失时显式告警。
- 理由：严格保持原样要求报告版式一致；离线服务器需要预先安装这些系统依赖。
- Linux 平台适配（相对基线报告的显式偏差，已实机验证并经确认）：
  - 编译引擎用 `latexmk + xelatex`：ctex 默认字体集 fandol 在 pdfTeX 下不可用，pdftex 可用的免费字体集不存在；
  - 基线 `width='360px'`（5 处）是非法 TeX 单位（LaTeX 报错后按 pt 恢复），显式改为 `360pt`，与恢复结果等价并使编译零错误；
  - ①-⑥ 圈号在 Latin Modern 缺字形，追加 `\xeCJKDeclareCharClass{CJK}{"2460 -> "24FF}` 映射到中文字体；
  - 安装与验证步骤记录在 `backend/docs/report-toolchain.md`。
- 备选与否决：改用 Python 原生 PDF（版式会变）→ 否决；pdflatex 路线不可行（见上）。

### D8 前端：Vue 3 + TypeScript 标准结构

- 选择：Vue 3 + TS + Vite + Vue Router + Pinia + Element Plus；3D 用 vtk.js；直方图用 Plotly.js（直接渲染后端返回的 figure JSON）。
- 理由：主流、易维护；Plotly.js 复用基线图表定义可避免口径漂移；vtk.js 与现有 stpyvista 同族，交互与配色最易对齐。
- 结构：`src/{api, assets, components, router, stores, views}`；核心组件 `Uploader`、`ArtifactPicker`、`JobProgress`、`PointCloudViewer`、`DeviationHistogram`。

### D9 部署：Linux 裸机 + uv + 静态托管

- 选择：前端 `npm run build` 产物 `frontend/dist` 由 FastAPI 静态托管（同源、单端口）；`backend/scripts/start.sh` 用 uv 启动 uvicorn（`0.0.0.0:PORT`，默认 8000 可配）；依赖安装清单写入 `backend/README.md`。
- 理由：单命令、单端口，B 端跨局域网最简；开发模式用 Vite dev server + 后端联调。
- 备选与否决：Nginx 反向代理更"生产"，但演示无需求；Docker 留待后续变更。

### D10 API 契约

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/uploads` | 初始化上传（filename/size）→ `upload_id` + 分片规格 |
| PUT | `/api/uploads/{id}/chunks/{index}` | 上传分片（幂等，携带 SHA-256）→ 已接收进度 |
| GET | `/api/uploads/{id}` | 查询已接收/缺失分片（续传依据） |
| POST | `/api/uploads/{id}/complete` | 合并 + 整体校验 + 登记产物（幂等） |
| DELETE | `/api/uploads/{id}` | 取消未完成上传并清理 |
| GET | `/api/session` | 会话快照：产物、任务、未完成上传（首次访问建立会话） |
| POST | `/api/tools/{tool}/jobs` | 提交任务（7 个工具 id，参数按工具校验）→ `job_id` |
| GET | `/api/jobs/{id}` | 状态/分步进度/失败原因；成功后返回结果载荷 |
| GET | `/api/artifacts/{id}/download` | 下载点云或 PDF（还原原名） |
| GET | `/api/artifacts/{id}/preview` | 轻量化预览二进制（含偏差标量） |
| GET | `/api/health` | 部署自检（TeX/Chromium/离屏渲染/字体） |

- 工具 id：`mesh-discretize`、`scale`、`downsample-voxel`、`downsample-uniform`、`register-fpfh`、`register-icp`、`quality-assess`。
- 双输入任务的请求体：`{"inputs": {"moving": "<artifact-id>", "fixed": "<artifact-id>"}, "params": {...}}`；单输入任务使用 `{"inputs": {"input": "<artifact-id>"}, "params": {...}}`。

### D11 数据模型

- `session.json` 结构（示意）：

```json
{
  "session_id": "...",
  "created_at": "...",
  "artifacts": [
    {"id": "...", "name": "BIM.xyz", "kind": "pointcloud", "size": 123,
     "created_at": "...", "source_job": "...", "path": "artifacts/<id>.xyz"}
  ],
  "jobs": [
    {"id": "...", "tool": "mesh-discretize", "status": "succeeded",
     "progress": {"stage": "第 2/2 步", "done": 2, "total": 2},
     "error": null, "result": {"artifact_ids": ["..."]},
     "created_at": "...", "updated_at": "..."}
  ],
  "uploads": [
    {"id": "...", "filename": "scan.xyz", "size": 123456789,
     "chunk_size": 8388608, "received": [0, 1, 3], "status": "uploading",
     "created_at": "...", "expires_at": "..."}
  ]
}
```

- 产物类型（kind）：`mesh`、`pointcloud`、`report`；预览数据为派生产物，不单独登记。
- 预览二进制：`MAGIC + version + JSON 头长度 + JSON 头（点数、字段、标量范围、名称）+ Float32 坐标 + 可选 Float32 标量/颜色`，小端序。

## 受影响文件与模块

- 新增 `backend/`：`app/{main.py, config.py, api/, core/, services/, algos/, jobs/}`、`scripts/start.sh`、`tests/`（含 golden 样例）、`README.md`（依赖安装清单）。
- 新增 `frontend/`：`src/{api, assets, components, router, stores, views}`、`package.json`、Vite/ESLint/Prettier 配置、`dist/` 构建产物（不入库）。
- 新增运行时数据目录 `data/sessions/**`（不入库）。
- 修改 `README.md`（新增 B/S 版本说明与启动入口）、`.gitignore`（`data/`、`frontend/node_modules/`、`frontend/dist/` 等）。
- 不改动 `base_software/**`（只作行为基线与 golden 对比来源）。

## 性能与安全影响

- 性能：Web 进程不做重计算；计算并发受池容量限制（默认 2，按 CPU/内存调整）；大文件分片流式落盘，内存占用不随文件大小增长；预览轻量化显著降低传输量；任务进度轮询 1 秒/任务，开销可忽略；磁盘侧由上传 TTL 与取消清理控制占用。
- 安全：无登录（仅限内网演示，部署文档建议绑定内网地址）；页面与接口不暴露服务器文件路径；下载/预览按会话 + 产物 id 访问，文件名净化防路径穿越；上传限制大小并逐分片校验 SHA-256；后端不执行用户文件内容；无数据库，无 SQL 注入面。

## Risks / Trade-offs

- [单 Web 实例] → 无横向扩展；重启会中断运行中任务（已定义为显式失败并给出原因）。
- [Linux 离屏渲染与中文字体] → 依赖清单 + `/api/health` 自检，缺失显式告警；容器化留待后续变更。
- [刷新后续传需重选文件] → 前端文件指纹匹配 + 明确提示；仅网络闪断可全自动续传。
- [大文件磁盘占用] → 分片 TTL 清理、可取消、文件大小上限可配。
- [轮询非实时] → 1 秒间隔满足演示；实时需求出现时再升级传输方式。
- [JSON 清单并发写] → 单 Web 实例 + 进程内锁 + 原子替换写。
- [numpy 2.x 与 open3d 0.16 不兼容（配准/ICP/RANSAC segfault）] → backend 固定 numpy 1.26.4；`base_software` 的锁定组合同样受影响（Linux 下配准/质量评估不可用），按约定本次不动 `base_software/`，作为后续独立变更处理。
- [报告点云图偏淡] → 基线 `draw1/draw2` 点尺寸=1 且 1024px 截图缩放到 360pt 后近似不可见；与基线代码行为一致，本次不修，如需改善另开变更。
- [算法缺陷保留] → golden 锁定现状，修复一律留待独立变更。

## Migration Plan

1. 建立 `backend/`、`frontend/` 骨架与配置（不改 `base_software/`）。
2. 搬迁算法到 `algos/` 并跑通 golden 对比；拆分报告相关模块。
3. 实现会话/存储、断点续传上传、任务执行与进度、产物下载与预览接口。
4. 逐工具端到端打通（网格离散 → 缩放/下采样 → 粗/精配准 → 质量评估与报告）。
5. 前端按原 UI 复刻全部页面并接入上述接口。
6. 部署脚本、依赖清单、启动自检、README 更新。
7. 端到端验收（含断点续传与大文件场景）。

- 回滚：本变更只新增目录与文档、不改 `base_software/`；停止新服务并删除新增目录/文档改动即恢复原状；运行时 `data/sessions/` 可直接删除。
- 上线：`uv sync` + 前端构建 + `backend/scripts/start.sh`；五冶按钮指向新地址。

## Open Questions

- 前端包管理器默认用 npm（若团队偏好 pnpm 可在实现时切换，不影响设计）。
- 离屏渲染的 Linux 实现（EGL/OSMesa 或 xvfb + mesa）在部署时实测选择，启动自检覆盖两种方案。
