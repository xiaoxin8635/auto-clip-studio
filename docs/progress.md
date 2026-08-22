# Progress

## 2026-08-22

- Defined MVP scope: long video upload, AI transcript and candidate segments, human review, 9:16 render, download.
- Created engineering standards, project skill, architecture notes, and API contract.
- Selected FastAPI + SQLite + React + FFmpeg.
- Runtime data is isolated under `.local/` and ignored by git.
- Added backend foundation: isolated configuration, SQLAlchemy models, SQLite initialization, project creation/detail API, and enforced state machine.
- Module gate: 6 focused tests passed; reviewed state transitions, storage isolation, error paths, and documentation consistency.
- Added upload validation, media probing, mock and OpenAI-compatible AI providers, schema validation, and asynchronous analysis pipeline.
- Module gate: 10 backend tests passed; reviewed upload limits, safe storage paths, provider output boundaries, retry states, and generated fixture isolation.
- Added segment editing, FFmpeg 9:16 rendering with caption burn-in, runtime path checks, rendered download API, and recoverable render failure state.
- Module gate: 15 backend tests passed, including a real upload -> analyze -> adjust -> render -> download end-to-end flow.
- Added React workbench for upload, status polling, transcript review, segment editing, rendering, and downloads.
- Module gate: frontend test and production build passed; reviewed polling boundaries, action disabling, error visibility, and API contract alignment.
- Added GitHub Actions CI for backend tests with FFmpeg and frontend test/build.
- M1: Added recent project summaries and frontend project recovery, so browser refresh no longer loses work.
- Module gate: backend project-list tests and frontend tests/build passed; contract and progress docs updated.
- M1: Hardened OpenAI-compatible provider with bounded transcript cues, retry/backoff for 408/429/5xx, transport error handling, and strict JSON extraction.
- Module gate: provider tests passed, including mocked rate-limit retry.
- M1: Added browser source preview per segment, a batch render endpoint, duplicate-render rejection through project state, and frontend batch action.
- Module gate: batch-render API tests and frontend test/build passed.
- M1: Added Alembic migrations, MIME allowlist validation, and orphan runtime-file cleanup.
- Module gate: focused cleanup/upload tests and full 20-test backend regression passed.
- M1: Added a 10-video real-provider evaluation plan and report placeholder.
- Hardened repository hygiene with broad media, secret, database, log, cache, and temporary-file ignore rules while preserving the required sample video fixture.
- Module gate: backend and frontend regressions passed; verified secret/media probes are ignored and the fixture remains tracked.
