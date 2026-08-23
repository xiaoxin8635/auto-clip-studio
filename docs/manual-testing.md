# Manual Testing Guide

This guide covers the two supported manual paths:

1. Offline mock flow: no API key required, validates the complete product workflow.
2. Real AI flow: DashScope ASR + GLM selector, validates the production provider chain.

## 1. Offline Mock Flow

Use this path for UI regression, rendering checks, and demos.

### Start Backend

```powershell
cd D:\ai_play\ai_agent_project\auto-clip-studio\backend
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:AUTOCLIP_PROVIDER="mock"
uvicorn app.main:app --reload
```

Expected terminal output:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

### Start Frontend

Open a second terminal:

```powershell
cd D:\ai_play\ai_agent_project\auto-clip-studio\frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

### Test Steps

1. Click create project.
2. Upload an MP4 or MOV file. The current limit is 500 MB.
3. Confirm the project card shows the uploaded filename and media duration.
4. Start analysis.
5. Wait for polling to reach `awaiting_review`; expected interval is about 2 seconds.
6. Verify the transcript area is non-empty.
7. Verify the app creates three candidate segments.
8. Edit one segment title and adjust its start/end time.
9. Confirm invalid values are rejected and valid values persist after refresh.
10. Use source preview and confirm the preview position matches the displayed segment time.
11. Render one segment.
12. Wait for `completed`.
13. Download the rendered MP4 and confirm it plays as a 9:16 vertical video.
14. Return to the workspace and confirm the project remains in recent projects after refresh.

### Mock Acceptance

- Upload, analysis, review, render, and download all complete without an API key.
- No unrecoverable `failed` state appears during the normal path.
- Rendered output exists and is playable.
- Browser refresh does not lose the current project.

## 2. Real AI Flow

Use this path only when DashScope and GLM credentials are available. Do not put keys in files committed to Git.

### Required Environment

In the backend terminal, set values before starting Uvicorn:

```powershell
$env:AUTOCLIP_PROVIDER="qwen-asr-openai-compatible"
$env:AUTOCLIP_ASR_API_KEY="<dashscope-key>"
$env:AUTOCLIP_AI_BASE_URL="<openai-compatible-base-url>"
$env:AUTOCLIP_AI_API_KEY="<selector-key>"
$env:AUTOCLIP_AI_MODEL="glm-5.3"
$env:AUTOCLIP_QWEN_ASR_MODEL="paraformer-v2"
$env:AUTOCLIP_OSS_BUCKET="<bucket>"
$env:AUTOCLIP_OSS_ENDPOINT="oss-cn-beijing.aliyuncs.com"
$env:AUTOCLIP_OSS_ACCESS_KEY_ID="<oss-key-id>"
$env:AUTOCLIP_OSS_ACCESS_KEY_SECRET="<oss-key-secret>"
uvicorn app.main:app --reload
```

Start the frontend exactly as in the mock flow.

### Test Steps

1. Create a project.
2. Upload a real MP4 or MOV video.
3. Start analysis.
4. Wait for transcription and segment selection. Long videos can take longer; the UI should keep polling.
5. Review the transcript and candidate segments.
6. Confirm all segment boundaries align to transcript cue boundaries.
7. Adjust one segment if needed.
8. Render and download one segment.
9. Play the result and check captions, crop, audio, and 9:16 aspect ratio.

### Real AI Acceptance

- Project status progresses through `transcribing`, `selecting`, and `awaiting_review`.
- Candidate segments contain non-empty titles, rationales, captions, and valid times.
- A provider failure moves the project to `failed` with a useful recoverable error.
- OSS audio is removed after ASR processing.
- No key appears in the UI, terminal logs, database, or Git changes.

## 3. Failure Checks

Run these negative checks in mock mode:

- Upload a non-video file: the API should reject it without changing project state to uploaded.
- Upload an oversized file: the API should reject it before storage.
- Trigger analysis twice in quick succession: the state machine should reject duplicate processing.
- Enter `end_ms <= start_ms`: the UI/API should reject the update.
- Render a segment after deleting its source file locally: the project should return to review state with a clear error.

## 4. Access-Token Check

For a deployment that enables authorization:

```powershell
$env:AUTOCLIP_API_TOKEN="<long-random-user-token>"
$env:AUTOCLIP_ADMIN_TOKEN="<different-long-random-admin-token>"
```

1. Start the frontend as usual.
2. Before setting a token, confirm the app shows a clear authentication error and the token input panel.
3. Click `设置 Token`, enter the exact `AUTOCLIP_API_TOKEN`, and save.
4. Confirm recent projects load and the normal workflow continues.
5. Click `更换 Token`, enter an invalid value, save, then refresh; the app should show 401 again.
6. Click `更换 Token`, then `清除`; the app must stop sending the stored token.
7. Render a segment and use the card download button; downloads use the stored Bearer token.

Token is stored only in browser `localStorage` under `autoclip_api_token`. Admin cleanup still must only accept the admin token, never the user token.

Known limitation: in token-protected mode, the inline source `<video>` preview cannot attach a custom Authorization header. The next media-delivery module should add a short-lived, scoped source URL. Until then, use the downloaded output for review when token protection is enabled; localhost mock mode without token protection keeps full preview functionality.
