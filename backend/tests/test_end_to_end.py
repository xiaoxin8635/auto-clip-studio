from test_upload_analysis import upload


def test_upload_analyze_adjust_render_and_download(client, created_project, temp_storage):
    project_id = created_project["id"]
    assert upload(client, project_id).status_code == 200
    assert client.post(f"/api/projects/{project_id}/analyze").status_code == 202
    detail = client.get(f"/api/projects/{project_id}").json()
    segment = detail["segments"][0]
    adjusted = client.patch(
        f"/api/projects/{project_id}/segments/{segment['id']}",
        json={"start_ms": 1000, "end_ms": 3000, "title": "Opening clip"},
    )
    assert adjusted.status_code == 200
    rendered = client.post(f"/api/projects/{project_id}/segments/{segment['id']}/render")
    assert rendered.status_code == 202
    final = client.get(f"/api/projects/{project_id}").json()
    assert final["status"] == "completed"
    download = client.get(f"/api/projects/{project_id}/segments/{segment['id']}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("video/mp4")
    assert len(download.content) > 1000
