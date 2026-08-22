# 架构

## 目标

AutoClip Studio 的 MVP 目标是保证一条可验证的垂直链路：上传视频，生成转录和候选片段，人工调整片段，渲染并下载 9:16 MP4。

## 组件

- `backend/app`：FastAPI 应用、API 路由、状态机、AI Provider 和渲染服务。
- `backend/tests`：后端单元测试、API 测试和端到端测试。
- `frontend/src`：React 工作台，负责上传、轮询状态、片段调整和下载。
- `.local`：运行时数据目录，保存 SQLite 数据库、上传视频、转录 JSON 和渲染产物。

## 数据流

1. 客户端创建项目。
2. 客户端上传 MP4/MOV，后端校验扩展名和大小后保存到 `.local/uploads`。
3. `analyze` 使用当前 Provider 生成转录和候选片段。
4. 用户调整片段后触发渲染。
5. 渲染服务调用 FFmpeg 裁切并输出 9:16 MP4 到 `.local/renders`。

## 状态机

```text
created -> uploaded -> transcribing -> selecting -> awaiting_review
awaiting_review -> rendering -> completed
rendering -> awaiting_review
任意执行态 -> failed
failed -> uploaded / awaiting_review / rendering
```

状态只能通过 `advance` / `fail` 变更，避免 API 直接写状态造成不可恢复的中间态。

## AI Provider

- `mock`：确定性输出，用于本地体验和测试。
- `openai-compatible`：通过标准 `/audio/transcriptions` 与 `/chat/completions` 接口访问兼容服务。
- `qwen-asr-openai-compatible`：DashScope 千问 ASR 负责时间戳转录，OpenAI-compatible LLM 负责选段。该模式要求 `AUTOCLIP_MEDIA_UPLOAD_URL_TEMPLATE` 提供一个可直接 PUT 上传并公开可下载的 URL 模板；生产环境可由 OSS 签名服务生成该模板。

Provider 输出必须先通过 Pydantic 校验，再进入数据库。网络或解析错误会转为项目失败状态，用户可重试。

## 部署边界

MVP 使用 SQLite 与 FastAPI BackgroundTasks，适合单机开发。多实例部署前应将数据库、任务队列和对象存储拆开。

## 数据库迁移

数据库结构变更通过 Alembic 管理：

```bash
cd backend
python -m alembic upgrade head
```

应用启动时会自动执行迁移；新库和既有库都兼容。
