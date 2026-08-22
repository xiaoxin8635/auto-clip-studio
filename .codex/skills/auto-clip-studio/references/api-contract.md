# API Contract

Base path: `/api`

## POST /projects

Creates a project. Body may be empty.

Response: `ProjectDetail`

## GET /projects?limit=

Returns recent project summaries in descending creation order. `limit` is clamped to 1-100 and defaults to 20.

Response fields: `id`, `status`, `source_filename`, `duration_ms`, `segment_count`, `created_at`, `error_message`.

## POST /projects/{project_id}/upload

 multipart/form-data field `file`, allowed `.mp4` and `.mov`, maximum 500 MiB.

Errors: `400` for invalid file, `409` for invalid state.

MIME type must be `video/mp4`, `video/quicktime`, or browser fallback `application/octet-stream`.

## POST /projects/{project_id}/analyze

Starts transcription and selection asynchronously. Allowed from `uploaded`, `failed` while an upload exists, and failed analysis retries.

Errors: `404`, `409`.

## GET /projects/{project_id}

Returns project status, transcript, and candidate segments. Poll this endpoint for progress.

## GET /projects/{project_id}/source

Streams the uploaded source video for browser preview. Requires an upload.

## PATCH /projects/{project_id}/segments/{segment_id}

JSON body may include `title`, `start_ms`, and `end_ms`. End must be after start and within the source duration.

Errors: `404`, `409`, `422`.

## POST /projects/{project_id}/segments/{segment_id}/render

Starts FFmpeg rendering. Allowed once the project is awaiting review.

Errors: `404`, `409`.

## POST /projects/{project_id}/render

Starts rendering all review-ready segments sequentially. Only allowed when the project is `awaiting_review`.

Response: `{"status":"rendering","count":N}`

## GET /projects/{project_id}/segments/{segment_id}/download

Downloads the rendered MP4.

Errors: `404`, `409`.

## Project status

`created`, `uploaded`, `transcribing`, `selecting`, `awaiting_review`, `rendering`, `completed`, `failed`
