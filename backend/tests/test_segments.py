from test_upload_analysis import upload


def analyzed_project(client, created_project):
    project_id = created_project["id"]
    assert upload(client, project_id).status_code == 200
    assert client.post(f"/api/projects/{project_id}/analyze").status_code == 202
    detail = client.get(f"/api/projects/{project_id}").json()
    assert detail["status"] == "awaiting_review"
    return detail


def test_segment_boundaries_can_be_updated(client, created_project):
    detail = analyzed_project(client, created_project)
    segment = detail["segments"][0]
    response = client.patch(
        f"/api/projects/{detail['id']}/segments/{segment['id']}",
        json={"title": "Opening", "start_ms": 1000, "end_ms": 4000},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Opening"
    assert response.json()["start_ms"] == 1000


def test_segment_rejects_out_of_range_boundary(client, created_project):
    detail = analyzed_project(client, created_project)
    segment = detail["segments"][0]
    response = client.patch(
        f"/api/projects/{detail['id']}/segments/{segment['id']}",
        json={"start_ms": 0, "end_ms": 999_999},
    )
    assert response.status_code == 422
