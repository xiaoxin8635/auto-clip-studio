from __future__ import annotations

import pytest

from app.config import get_settings
from app.db import init_db, reset_db_cache
from app.main import app
from app.models import Project
from fastapi.testclient import TestClient


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    data_dir = tmp_path / "local"
    monkeypatch.setenv("AUTOCLIP_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    yield data_dir
    get_settings.cache_clear()
    reset_db_cache()
    return data_dir


@pytest.fixture
def client(temp_storage):
    init_db()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def created_project(client):
    response = client.post("/api/projects")
    assert response.status_code == 201
    return response.json()
