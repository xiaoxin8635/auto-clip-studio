# Module Workflow

Implement modules in order unless the user explicitly changes scope:

1. Project skeleton and configuration.
2. Data models, database initialization, and state machine.
3. Project creation and upload API.
4. Transcription provider.
5. Segment-selection provider and analysis orchestration.
6. Segment adjustment API.
7. FFmpeg rendering worker and download API.
8. Frontend upload and progress workspace.
9. Frontend segment review and render actions.
10. End-to-end regression and release readiness.

For every module:

```text
implement -> add focused tests -> run tests
-> run review checklist -> fix findings -> rerun tests
-> update docs/progress.md -> commit
```

If a dependency or environment tool is unavailable, preserve a clear failure state and user-facing recovery action rather than blocking the whole application.
