from app.config import get_settings


def test_api_endpoints_allow_local_access_without_token(client):
    assert client.get("/api/projects").status_code == 200


def test_api_endpoints_require_bearer_token_when_configured(client, monkeypatch):
    monkeypatch.setenv("AUTOCLIP_API_TOKEN", "user-token")
    get_settings.cache_clear()

    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Basic user-token"}).status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer user-token"}).status_code == 200


def test_admin_cleanup_requires_configured_admin_token(client, monkeypatch):
    assert client.post("/api/admin/runtime/cleanup").status_code == 503

    monkeypatch.setenv("AUTOCLIP_API_TOKEN", "user-token")
    monkeypatch.setenv("AUTOCLIP_ADMIN_TOKEN", "admin-token")
    get_settings.cache_clear()
    assert client.post(
        "/api/admin/runtime/cleanup", headers={"Authorization": "Bearer user-token"}
    ).status_code == 403
    assert client.post(
        "/api/admin/runtime/cleanup", headers={"Authorization": "Bearer admin-token"}
    ).status_code == 200
