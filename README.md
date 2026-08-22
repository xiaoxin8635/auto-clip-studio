# AutoClip Studio

AutoClip Studio 是一个可本地运行的自动剪辑工作台：上传长视频，生成转录和候选短片，人工确认片段后渲染 9:16 MP4。

## 功能

- 上传 MP4/MOV 视频
- 使用 mock 或 OpenAI-compatible 服务生成转录与候选片段
- 调整候选片段标题和起止时间
- 使用 FFmpeg 渲染 9:16 竖屏短片
- 在浏览器中下载渲染结果

## 快速开始

后端：

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

默认后端地址为 `http://127.0.0.1:8000`。生产构建使用 `npm run build`。

## AI Provider

默认 Provider 为 `mock`，无需 API key 即可跑通完整流程。

如需 OpenAI-compatible 服务，设置：

```text
AUTOCLIP_PROVIDER=openai-compatible
AUTOCLIP_AI_BASE_URL=https://api.example.com/v1
AUTOCLIP_AI_API_KEY=your-key
AUTOCLIP_AI_MODEL=your-model
```

可选配置：

```text
AUTOCLIP_TRANSCRIBE_MODEL=your-asr-model
AUTOCLIP_CAPTION_SUFFIX=.srt
```

也可以使用千问 ASR + LLM 选段的组合：

```text
AUTOCLIP_PROVIDER=qwen-asr-openai-compatible
AUTOCLIP_QWEN_ASR_MODEL=qwen-audio-asr
AUTOCLIP_MEDIA_UPLOAD_URL_TEMPLATE=https://your-storage.example/{name}?signature=...
AUTOCLIP_AI_BASE_URL=https://peuyai.ulib.top/v1
AUTOCLIP_AI_API_KEY=your-key
AUTOCLIP_AI_MODEL=glm-5.3
```

千问 ASR 要求音频具有可下载 URL。上传模板必须支持 `PUT`，并把 `{name}` 替换为文件名；生产环境应由 OSS 签名服务生成短期 URL，后端只使用该 URL，不保存 OSS 密钥。

- `AUTOCLIP_AI_MODEL` 用于片段选择。
- `AUTOCLIP_TRANSCRIBE_MODEL` 用于音频转录；未设置时沿用 `AUTOCLIP_AI_MODEL`。
- `AUTOCLIP_CAPTION_SUFFIX` 设置后优先读取上传文件旁边的本地字幕，适合评测已带官方字幕的素材。

密钥只能通过环境变量注入，不能提交到仓库。

## 开发流程

本项目的开发顺序、接口契约和 review 门禁定义在 `.codex/skills/auto-clip-studio/`。每次新增或修改接口/模块时，必须完成测试、review、文档同步后再提交。

## 许可证

MIT
