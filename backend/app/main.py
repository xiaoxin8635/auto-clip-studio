from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from .config import get_settings
from .db import init_db, session_scope
from .models import Project
from .serialization import project_to_out
from .schemas import ProjectCreate


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
        project = session.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_to_out(project)
