"""
Example integration tests for API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns 200."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health endpoint."""
        response = await client.get("/api/v2/system/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


@pytest.mark.integration
class TestVideoEndpoints:
    """Test video-related endpoints."""

    @pytest.mark.asyncio
    async def test_video_info_invalid_platform(self, client: AsyncClient):
        """Test video info with invalid platform."""
        response = await client.get("/api/v2/videos/invalid/test123")
        # Should return 400 or 404
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_video_info_missing_id(self, client: AsyncClient):
        """Test video info with missing ID."""
        response = await client.get("/api/v2/videos/youtube/")
        # Should return 404
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.slow
class TestStreamingEndpoints:
    """Test streaming endpoints."""

    @pytest.mark.asyncio
    async def test_stream_endpoint_requires_video_id(self, client: AsyncClient):
        """Test streaming requires video ID."""
        response = await client.get("/api/v2/stream/proxy/youtube/")
        assert response.status_code == 404
