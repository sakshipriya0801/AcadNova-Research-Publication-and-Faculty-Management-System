"""Health endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_health_is_ok():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
