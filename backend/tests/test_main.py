from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_status_message():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "CodePilot backend is running"}


def test_health_endpoint_returns_service_status():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "codepilot-api"}
