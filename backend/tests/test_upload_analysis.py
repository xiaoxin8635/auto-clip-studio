from pathlib import Path

from helpers import create_test_video


def upload(client, project_id, filename="sample.mp4", content=None, content_type="video/mp4"):
    path = Path(__file__).parent / "fixtures" / filename
    if content is None:
        if not path.exists():
            create_test_video(path, seconds=20)
        content = path.read_bytes()
    return client.post(
        f"/api/projects/{project_id}/upload",
        files={"file": (filename, content, content_type)},
    )


def test_upload_and_analyze_with_mock(client, created_project, temp_storage):
    project_id = created_project["id"]
    uploaded = upload(client, project_id)
    assert uploaded.status_code == 200
    assert uploaded.json()["status"] == "uploaded"
    assert uploaded.json()["duration_ms"] >= 19_000
    assert (temp_storage / "uploads" / f"{project_id}.mp4").exists()

    analyzed = client.post(f"/api/projects/{project_id}/analyze")
    assert analyzed.status_code == 202
    detail = client.get(f"/api/projects/{project_id}").json()
    assert detail["status"] == "awaiting_review"
    assert len(detail["segments"]) == 3
    assert detail["transcript_text"]


def test_upload_rejects_wrong_extension(client, created_project):
    response = upload(client, created_project["id"], "movie.txt", b"not video", "text/plain")
    assert response.status_code == 400
    assert response.json()["detail"] == "Only MP4 and MOV files are supported"


def test_upload_rejects_second_upload(client, created_project):
    assert upload(client, created_project["id"]).status_code == 200
    assert upload(client, created_project["id"]).status_code == 409
