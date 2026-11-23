import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("CEREPATH_OWNER_TOKEN", "test-owner-token-that-is-long-enough")
os.environ.setdefault("BROWSER_INTERNAL_TOKEN", "test-browser-token-that-is-long-enough")

from fastapi.testclient import TestClient

from app.main import app


def test_health_payload_uses_cerepath_identity():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["service"] == "cerepath-api"
