---
type: runtime-architecture
title: 运行时状态、会话与路径
description: 说明 data/sessions 工作区、session.json、artifacts/uploads/previews/work 子目录、锁与原子写，以及 base_software cache 文本状态协议的历史差异。
tags: [architecture, state, persistence, sessions, filesystem]
verified:
  - by: openwiki/0.5.1
    at: 2026-09-29T03:28:02.619Z
sources:
  - id: openwiki-source-d3cb6830ecaa081440b96d80
    resource: repo://backend/app/api/session.py
  - id: openwiki-source-4188bfee2e15d969d3152477
    resource: repo://backend/app/config.py
  - id: openwiki-source-8803caea915c45463e82f840
    resource: repo://backend/app/core/artifacts.py
  - id: openwiki-source-7c751c107cacf372c92785f6
    resource: repo://backend/app/core/preview.py
  - id: openwiki-source-641ae98462ef0e5867e3c63c
    resource: repo://backend/app/core/sessions.py
  - id: openwiki-source-af8bc07dd356b94582111a05
    resource: repo://backend/app/core/uploads.py
  - id: openwiki-source-5cd8a5b32eb393895819dfdc
    resource: repo://backend/app/jobs/runner.py
  - id: openwiki-source-24a943f3d4ce3be6822a4891
    resource: repo://backend/app/jobs/store.py
  - id: openwiki-source-b735a19d109c0dd7887674e9
    resource: repo://base_software/functions/PDF.py
  - id: openwiki-source-d69beca5a040440e55fef3c1
    resource: repo://base_software/home_page.py
  - id: openwiki-source-db642bdc773df44d5cdde189
    resource: repo://base_software/pages/1_%F0%9F%9B%A0%EF%B8%8F_%E7%82%B9%E4%BA%91%E9%A2%84%E5%A4%84%E7%90%86.py
  - id: openwiki-source-4829642f91ca54c265d248ed
    resource: repo://base_software/pages/2_%F0%9F%96%A5%EF%B8%8F_%E5%B0%BA%E5%AF%B8%E8%B4%A8%E9%87%8F%E8%AF%84%E4%BC%B0.py
  - id: openwiki-source-f62fb78e9932aaca3ecc6806
    resource: repo://base_software/path_utils.py
generated: { by: "codex", at: "2026-09-29T03:28:02.619Z" }
---

# 运行时状态、会话与路径

## 数据根目录

B/S 版本的根目录由 `WUYE_DATA_DIR` 决定，默认是仓库根目录下的 `data/`；会话根目录为 `DATA_DIR / 'sessions'`。每个浏览器会话访问自己的 `data/sessions/<uuid>/`，不同会话的产物和任务默认互不可见。

`session.json` 是当前会话的唯一真源，记录：

- `session_id` 和创建时间；
- `artifacts`：已登记的输入和输出产物；
- `uploads`：上传记录、已接收分片和分片哈希；
- `jobs`：任务状态、参数、结果和内部交接信息。

`SessionStore` 为每个 session id 维护进程内锁，并在锁内执行读-改-写；写文件时先写 `session.json.tmp`，再用 `os.replace()` 原子替换。这个设计面向单 Web 实例，不提供跨实例分布式锁。

## 会话目录布局

`SessionStore` 的目录约定如下：

```text
data/sessions/<session_id>/
  session.json
  artifacts/
    <artifact_id><suffix>
  uploads/
    <upload_id>/
      chunks/<index>.part
  previews/
    artifact-<artifact_id>.bin
    job-<job_id>.bin
  work/
    <job_id>/
      state.json
      progress.json
      cache/...
```

各子目录的生命周期不同：

- `artifacts/`：成功产物的内部存储，文件名使用 artifact id，下载时恢复会话清单中的显示名称。
- `uploads/`：未完成上传的临时目录；完成后合并并登记产物，然后删除该上传目录。
- `previews/`：按 artifact 或 job id 缓存的 WYPV 预览；缓存命中时不再读取全量点云。
- `work/`：单个任务的工作目录，保存运行状态、阶段进度和算法中间文件。

## 产物与路径安全

`register_artifact()` 对显示名称做路径净化，只保留最后一个路径组件，拒绝空名和 `.`/`..`。内部存储路径采用 `artifacts/<uuid><suffix>`，因此同名输入不会互相覆盖。

`artifact_path()` 在返回文件路径前把候选路径解析为绝对路径，并验证它仍位于当前会话目录内；路径穿越或伪造存储路径会被拒绝。API 层只返回产物 id、显示名称、类型、大小和时间，不暴露内部 `path` 字段。

## 上传状态

上传记录保存在 `session.json` 的 `uploads` 数组中。分片接收时：

1. 按分片索引判断是否已经接收；重复提交直接返回当前进度。
2. 检查分片长度和 `X-Chunk-SHA256`。
3. 先把分片写入 `.part.tmp`，再原子替换为 `<index>.part`。
4. 在会话锁内记录已接收索引和分片哈希。

完成上传时，`_assemble()` 按索引顺序读取所有分片，逐一重新校验长度和哈希，再计算整体 SHA-256；通过后由 `register_artifact()` 登记产物，并删除上传临时目录。若校验失败且错误包含具体分片索引，会删除该分片并从 `received` 中移除，允许后续重传；其他失败会在 `completing` 状态下恢复为 `uploading` 或显式抛出。

未完成上传可以由用户取消，超过 `WUYE_UPLOAD_TTL_SECONDS` 的记录会在后续初始化上传时惰性清理。TTL 清理不会回收已经完成的产物。

## 任务状态与工作目录

任务记录写入 `session.json` 的 `jobs` 数组，但运行中的阶段进度不直接由 worker 写回该文件。`JobRunner` 在工作目录中维护：

- `state.json`：worker 启动时写入 `running` 和进程号。
- `progress.json`：worker 调用 `progress(stage, done, total)` 时原子写入阶段、完成数和总数。

查询任务时，`view_job()` 把会话记录、`state.json` 和 `progress.json` 合并成 API 视图。服务启动时 `interrupt_leftover_jobs()` 扫描所有会话，把遗留的 `queued`/`running` 任务显式标记为 `interrupted`，而不是继续等待不存在的进程。

任务成功后，完成回调会把输出路径登记为 artifact，并把结果摘要和内部输出写回任务记录；任务失败则保留简洁错误文本，不把半成品登记为成功产物。

## 会话 API 的去敏边界

`GET /api/session` 返回会话快照时会移除：

- artifact 的内部 `path`；
- upload 的 `chunk_sha256` 映射；
- job 的 `internal` 字段。

这样浏览器获得的是可用于选择和展示的元数据，而不是服务器文件路径或内部错误云位置。会话 cookie 只负责标识工作区，不提供用户身份认证。

## 历史基线的状态协议

`base_software/` 使用完全不同的状态模型：

- `path_utils.get_app_base_path()` 在冻结环境返回 `sys._MEIPASS`，在源码环境根据 `pages`、`functions`、`interface` 目录查找应用根；未命中时返回模块所在目录。
- `get_cache_path()` 在应用根下创建 `cache/`，首页初始化也会创建同一目录。
- 页面用纯文本文件保存输入、输出和交接路径，例如 `Tool_*_Input.txt`、`Tool_*_Output.txt`、`Tool_Registration_ICP_SCENE.txt`、`QA_pcd.txt` 等；没有数据库、`session_state`、pickle 或结构化配置。
- 每次重新选择都会直接覆盖对应文本文件，文件没有版本号、结构校验或并发锁。
- FPFH 粗配准成功后把 `_FPFH.xyz` 路径写入 `Tool_Registration_ICP_SCENE.txt`，作为精配准的建议输入；质量评估只读取用户通过 `QA_pcd.txt` 选择的扫描点云，不会自动读取该预处理输出。
- 多数计算入口直接打开前置缓存文件；文件不存在时会产生 `FileNotFoundError`，而不是统一领域错误。
- Tk 文件对话框取消时返回的空字符串仍可能写进缓存，后续流程不会把空路径识别为“取消”。
- 质量评估会在同一缓存目录中以固定文件名覆盖 `fig1a.jpg`、`fig1b.jpg`、`fig2.jpg`、`fig3.jpg`、`fig4.jpg`、`fig5.jpg` 和 `Error_Analysis.jpg`。
- 精配准的“打开输出文件夹”曾用前导斜杠文件名与 `cache_path` 拼接，导致它被解析为文件系统根路径下的文件；这是历史实现的已知路径边界，不是 B/S 版本的行为。

当前 B/S 版本保留算法与报告语义，但不再复用这套跨页面文本缓存协议。

## 相关页面

- [浏览器—服务端架构](browser-server-architecture.md)
- [会话、上传与产物工作流](../workflows/session-upload-and-artifacts.md)
- [异步任务执行与进度](../workflows/async-job-execution.md)
- [点云预览管线](point-cloud-preview-pipeline.md)
