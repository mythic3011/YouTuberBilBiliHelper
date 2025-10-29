"""
Pytest configuration and fixtures.
"""

import asyncio
import pytest
from typing import Generator, AsyncGenerator
from httpx import AsyncClient

from app.main import app
from app.services.redis_service import redis_service


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator:
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def redis():
    """Get Redis connection pool."""
    pool = await redis_service.get_pool()
    yield pool
    # Cleanup
    await pool.flushdb()


@pytest.fixture
def sample_video_data():
    """Sample video data for testing."""
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Test Video",
        "platform": "youtube",
        "duration": 212,
        "thumbnail": "https://example.com/thumb.jpg",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }


@pytest.fixture
def sample_bilibili_data():
    """Sample Bilibili video data for testing."""
    return {
        "id": "BV1xx411c7XD",
        "title": "Test Bilibili Video",
        "platform": "bilibili",
        "duration": 300,
        "thumbnail": "https://example.com/thumb.jpg",
        "url": "https://www.bilibili.com/video/BV1xx411c7XD"
    }
