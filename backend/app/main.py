from __future__ import annotations

import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from .config import get_settings
from .db import init_db, session_scope
from .media import MediaToolError, probe_media
from .models import Project
from .pipeline import run_analysis
from .schemas import ProjectCreate
from .serialization import project_to_out
from .state_machine import InvalidTransitionError, advance


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="AutoClip Studio API", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": get_settings().provider}


@app.post("/api/projects", status_code=201)
def create_project(response: Response, _: ProjectCreate | None = None):
    with session_scope() as session:
        project = Project(status="created")
        session.add(project)
        session.flush()
        result = project_to_out(project)
        project_id = project.id
    response.headers["Location"] = f"/api/projects/{project_id}"
    return result


@app.get("/api/projects/{project_id}")
def project_detail(project_id: str):
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        return project_to_out(project)


@app.post("/api/projects/{project_id}/upload")
def upload_video(project_id: str, file: UploadFile = File(...)):
    settings = get_settings()
    safe_suffix = Path(file.filename or "").suffix.lower()
    if safe_suffix not in {".mp4", ".mov"}:
        raise HTTPException(status_code=400, detail="Only MP4 and MOV files are supported")
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{project_id}{safe_suffix}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=400, detail="File exceeds the 500 MB limit")
                output.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    with session_scope() as session:
        project = _get_project_or_404(session, project_id)
        try:
            if project.status != "created":
                raise HTTPException(status_code=409, detail="Project is not accepting an upload")
            try:
                info = probe_media(destination)
            except MediaToolError as exc:
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            project.source_filename = unicodedata.normalize("NFKC", file.filename or destination.name)
            project.source_path = str(destination)
            project.duration_ms = info.duration_ms
            advance(project, "uploaded")
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=409, detail="Project is not accepting an upload") from exc
        return project_to_out(project)


@app.post("/api/projects/{project_id}/analyze", status_code=202)
def analyze_video(project_id: str, background_tasks: BackgroundTasks):
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


def _get_project_or_404(session: Session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
