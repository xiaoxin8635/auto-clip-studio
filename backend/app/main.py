from __future__ import annotations

import unicodedata
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Response, Security, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .config import get_settings
from .db import init_db, session_scope
from .media import MediaToolError, probe_media
from .models import Project, Segment
from .pipeline import run_analysis
from .rendering import run_render, run_render_batch
from .schemas import ProjectCreate
from .schemas import SegmentUpdate
from .serialization import project_to_out
from .serialization import project_to_summary
from .state_machine import InvalidTransitionError, advance
from fastapi import Request


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    command.upgrade(Config("alembic.ini"), "head")
    yield


app = FastAPI(title="AutoClip Studio API", version="0.1.0", lifespan=lifespan)

_bearer_scheme = HTTPBearer(auto_error=False)


def require_api_access(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
):
    settings = get_settings()
    if not settings.api_token:
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer authentication is required")
    if not secrets.compare_digest(credentials.credentials, settings.api_token):
        raise HTTPException(status_code=401, detail="Invalid API token")
    return credentials.credentials


def require_admin(request: Request):
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="Admin token is not configured")
    credentials = request.headers.get("Authorization", "")
    scheme, _, token = credentials.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return token


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": get_settings().provider}


@app.post("/api/projects", status_code=201)
def create_project(response: Response, _: ProjectCreate | None = None, __: str | None = Depends(require_api_access)):
    with session_scope() as session:
        project = Project(status="created")
        session.add(project)
        session.flush()
        result = project_to_out(project)
        project_id = project.id
    response.headers["Location"] = f"/api/projects/{project_id}"
    return result


@app.get("/api/projects")
def list_projects(limit: int = 20, _: str | None = Depends(require_api_access)):
    limit = min(max(limit, 1), 100)
    with session_scope() as session:
        projects = session.scalars(select(Project).order_by(desc(Project.created_at)).limit(limit)).all()
        return {"items": [project_to_summary(project) for project in projects]}


@app.get("/api/projects/{project_id}")
def project_detail(project_id: str, _: str | None = Depends(require_api_access)):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        return project_to_out(project)


@app.get("/api/projects/{project_id}/source")
def project_source(project_id: str, _: str | None = Depends(require_api_access)):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        if not project.source_path:
            raise HTTPException(status_code=409, detail="Project has no uploaded video")
        return FileResponse(project.source_path, media_type="video/mp4")


@app.post("/api/projects/{project_id}/upload")
def upload_video(project_id: str, file: UploadFile = File(...), _: str | None = Depends(require_api_access)):
    settings = get_settings()
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        if project.status != "created":
            raise HTTPException(status_code=409, detail="Project is not accepting an upload")
    safe_suffix = Path(file.filename or "").suffix.lower()
    if safe_suffix not in {".mp4", ".mov"}:
        raise HTTPException(status_code=400, detail="Only MP4 and MOV files are supported")
    if (file.content_type or "").lower() not in {"video/mp4", "video/quicktime", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Unsupported video MIME type")
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{project_id}{safe_suffix}"
    temporary = destination.with_suffix(destination.suffix + ".part")
    size = 0
    try:
        with temporary.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=400, detail="File exceeds the 500 MB limit")
                output.write(chunk)
    except HTTPException:
        temporary.unlink(missing_ok=True)
        raise
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        try:
            if project.status != "created":
                raise HTTPException(status_code=409, detail="Project is not accepting an upload")
            try:
                info = probe_media(temporary)
            except MediaToolError as exc:
                temporary.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            temporary.replace(destination)
            project.source_filename = unicodedata.normalize("NFKC", file.filename or destination.name)
            project.source_path = str(destination)
            project.duration_ms = info.duration_ms
            advance(project, "uploaded")
        except InvalidTransitionError as exc:
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail="Project is not accepting an upload") from exc
        return project_to_out(project)


@app.post("/api/admin/runtime/cleanup")
def cleanup_runtime_files(_: str = Depends(require_admin)):
    settings = get_settings()
    with session_scope() as session:
        valid_paths = {
            path
            for path in session.scalars(select(Project.source_path)).all()
            if path
        } | {
            segment.output_path
            for segment in session.scalars(select(Segment)).all()
            if segment.output_path
        }
    removed = []
    for directory in ("uploads", "renders"):
        runtime_dir = settings.data_dir / directory
        if not runtime_dir.exists():
            continue
        for path in runtime_dir.iterdir():
            if str(path) not in valid_paths:
                path.unlink(missing_ok=True)
                removed.append(str(path))
    return {"removed_count": len(removed), "removed": removed}


@app.post("/api/projects/{project_id}/analyze", status_code=202)
def analyze_video(project_id: str, background_tasks: BackgroundTasks, _: str | None = Depends(require_api_access)):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        if project.status not in {"uploaded", "failed"} or not project.source_path:
            raise HTTPException(status_code=409, detail="Project must be uploaded before analysis")
        try:
            advance(project, "transcribing")
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=409, detail="Project cannot start analysis") from exc
    background_tasks.add_task(run_analysis, project_id)
    return {"status": "transcribing"}


@app.patch("/api/projects/{project_id}/segments/{segment_id}")
def update_segment(
    project_id: str,
    segment_id: str,
    payload: SegmentUpdate,
    _: str | None = Depends(require_api_access),
):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        segment = _get_segment_or_404(project, segment_id)
        if project.status not in {"awaiting_review", "failed"}:
            raise HTTPException(status_code=409, detail="Segments can only be edited during review")
        start = payload.start_ms if payload.start_ms is not None else segment.start_ms
        end = payload.end_ms if payload.end_ms is not None else segment.end_ms
        if start < 0 or end <= start or (project.duration_ms and end > project.duration_ms):
            raise HTTPException(status_code=422, detail="Segment boundaries are invalid")
        if payload.title is not None:
            segment.title = payload.title
        segment.start_ms = start
        segment.end_ms = end
        segment.status = "updated"
        return {
            "id": segment.id,
            "title": segment.title,
            "rationale": segment.rationale,
            "start_ms": segment.start_ms,
            "end_ms": segment.end_ms,
            "caption_text": segment.caption_text,
            "status": segment.status,
            "download_url": None,
        }


@app.post("/api/projects/{project_id}/segments/{segment_id}/render", status_code=202)
def render_segment(
    project_id: str,
    segment_id: str,
    background_tasks: BackgroundTasks,
    _: str | None = Depends(require_api_access),
):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        segment = _get_segment_or_404(project, segment_id)
        if project.status not in {"awaiting_review", "completed", "failed"}:
            raise HTTPException(status_code=409, detail="Project must be awaiting review before rendering")
        try:
            advance(project, "rendering")
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=409, detail="Project cannot start rendering") from exc
    background_tasks.add_task(run_render, project_id, segment_id)
    return {"status": "rendering"}


@app.post("/api/projects/{project_id}/render", status_code=202)
def render_all_segments(
    project_id: str,
    background_tasks: BackgroundTasks,
    _: str | None = Depends(require_api_access),
):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        if project.status != "awaiting_review" or not project.segments:
            raise HTTPException(status_code=409, detail="Project must have review-ready segments")
        segment_count = len(project.segments)
        try:
            advance(project, "rendering")
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=409, detail="Project cannot start rendering") from exc
    background_tasks.add_task(run_render_batch, project_id)
    return {"status": "rendering", "count": segment_count}


@app.get("/api/projects/{project_id}/segments/{segment_id}/download")
def download_segment(project_id: str, segment_id: str, _: str | None = Depends(require_api_access)):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        segment = _get_segment_or_404(project, segment_id)
        if not segment.output_path or project.status != "completed":
            raise HTTPException(status_code=409, detail="Segment has not been rendered")
        return FileResponse(segment.output_path, media_type="video/mp4", filename=f"{segment.title}.mp4")


def _get_project_or_404(session: Session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_segment_or_404(project: Project, segment_id: str):
    segment = next((item for item in project.segments if item.id == segment_id), None)
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment
