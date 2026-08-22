from pathlib import Path


def test_cleanup_removes_orphan_files(client, temp_storage):
    uploads = temp_storage / "uploads"
    uploads.mkdir(parents=True)
    orphan = uploads / "orphan.mp4"
    orphan.write_bytes(b"orphan")
    response = client.post("/api/admin/runtime/cleanup")
    assert response.status_code == 200
    assert response.json()["removed_count"] == 1
    assert not orphan.exists()
