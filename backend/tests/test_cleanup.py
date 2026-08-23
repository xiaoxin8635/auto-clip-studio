from pathlib import Path

from app.config import get_settings


def test_cleanup_removes_orphan_files(client, temp_storage, monkeypatch):
    monkeypatch.setenv("AUTOCLIP_ADMIN_TOKEN", "admin-token")
    get_settings.cache_clear()
    uploads = temp_storage / "uploads"
    uploads.mkdir(parents=True)
    orphan = uploads / "orphan.mp4"
    orphan.write_bytes(b"orphan")
    response = client.post("/api/admin/runtime/cleanup", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    assert response.json()["removed_count"] == 1
    assert not orphan.exists()
