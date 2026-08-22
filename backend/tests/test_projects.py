def test_project_is_created(client):
    response = client.post("/api/projects")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created"
    assert body["segments"] == []
    assert response.headers["location"].endswith(f"/api/projects/{body['id']}")


def test_project_detail_is_returned(client, created_project):
    response = client.get(f"/api/projects/{created_project['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_project["id"]


def test_missing_project_returns_404(client):
    response = client.get("/api/projects/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
