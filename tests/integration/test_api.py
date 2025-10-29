"""Basic API tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["version"] == "2.0.0"


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v2/system/health")
    assert response.status_code in [200, 500]  # May fail if Redis not available
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


def test_version_endpoint():
    """Test version endpoint."""
    response = client.get("/api/v2/system/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["version"] == "2.0.0"


def test_openapi_docs():
    """Test OpenAPI documentation."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data


def test_video_info_invalid_url():
    """Test video info with invalid URL."""
    response = client.post("/api/v2/videos/info", json={
        "url": "https://invalid-domain.com/video"
    })
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_storage_info():
    """Test storage info endpoint."""
    response = client.get("/api/v2/system/storage")
    assert response.status_code == 200
    data = response.json()
    assert "total_space_gb" in data
    assert "used_space_gb" in data


if __name__ == "__main__":
    pytest.main([__file__])
