from test_upload_analysis import upload


def test_batch_render_requires_review(client, created_project):
    assert client.post(f"/api/projects/{created_project['id']}/render").status_code == 409


def test_batch_render_queues_all_segments(client, created_project):
    project_id = created_project["id"]
    assert upload(client, project_id).status_code == 200
    assert client.post(f"/api/projects/{project_id}/analyze").status_code == 202
    response = client.post(f"/api/projects/{project_id}/render")
    assert response.status_code == 202
    assert response.json()["count"] == 3
    detail = client.get(f"/api/projects/{project_id}").json()
    assert detail["status"] == "completed"
    assert len(detail["segments"]) == 3
    assert all(segment["download_url"] for segment in detail["segments"])
