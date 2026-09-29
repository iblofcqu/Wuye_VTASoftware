# 文件

- [仓库与应用架构总览](application-overview.md) - 说明 monorepo 中 frontend、backend、base_software、docs、openspec 与 openwiki 的职责边界，以及 B/S 实现作为当前主路径、Streamlit 实现作为行为基线的定位。
- [浏览器—服务端架构](browser-server-architecture.md) - 说明 Vue 前端、FastAPI 同源服务、会话中间件、业务 API、计算进程池与质量评估报告 supervisor 之间的运行时关系，以及浏览器结果渲染边界。
- [点云预览管线](point-cloud-preview-pipeline.md) - 说明服务端点云轻量化与 WYPV 二进制编码、会话内缓存和预览 API，以及前端解析、vtk.js 渲染、配色和 WebGL2 不可用时的失败边界。
- [运行时状态、会话与路径](runtime-state-and-paths.md) - 说明 data/sessions 工作区、session.json、artifacts/uploads/previews/work 子目录、质量评估报告子进程状态文件、锁与原子写，以及 base_software cache 文本状态协议的历史差异。
