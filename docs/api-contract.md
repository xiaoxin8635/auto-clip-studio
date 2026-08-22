# API Contract

See `.codex/skills/auto-clip-studio/references/api-contract.md` for the canonical contract. Keep both copies synchronized whenever an endpoint changes.

Current endpoints:

- `POST /api/projects`
- `POST /api/projects/{project_id}/upload`
- `POST /api/projects/{project_id}/analyze`
- `GET /api/projects/{project_id}`
- `PATCH /api/projects/{project_id}/segments/{segment_id}`
- `POST /api/projects/{project_id}/segments/{segment_id}/render`
- `GET /api/projects/{project_id}/segments/{segment_id}/download`
