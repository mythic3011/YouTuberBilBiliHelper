# YouTuberBilBiliHelper - Implementation Guide

## 🚀 Getting Started with the Enhancement Plan

This guide provides step-by-step instructions for implementing the improvements outlined in the improvement plan and roadmap.

## 📋 Prerequisites

### Development Environment
- **Python 3.11+**: Latest Python version with async support
- **Node.js 18+**: For frontend development and build tools
- **Docker & Docker Compose**: For containerization and local development
- **PostgreSQL 14+**: Primary database
- **Redis 7+**: Caching and session storage
- **Git**: Version control

### Development Tools
- **VS Code/PyCharm**: IDE with Python and TypeScript support
- **Postman/Insomnia**: API testing
- **pgAdmin/DBeaver**: Database management
- **Redis CLI**: Redis database management

### Cloud Services (Optional)
- **AWS/GCP/Azure**: Cloud infrastructure
- **Cloudflare**: CDN and DNS
- **Sentry**: Error tracking
- **DataDog/New Relic**: Monitoring and analytics

## 🏗️ Phase 1 Implementation: Platform Expansion

### Step 1: Set Up Enhanced Development Environment

#### 1.1 Create Development Branch
```bash
# Create development branch for Phase 1
git checkout -b phase1-platform-expansion
git push -u origin phase1-platform-expansion
```

#### 1.2 Update Project Structure
```bash
# Create new directory structure
mkdir -p app/platforms
mkdir -p app/core
mkdir -p app/database
mkdir -p app/ai
mkdir -p frontend
mkdir -p mobile
mkdir -p browser-extensions
mkdir -p infrastructure
mkdir -p tests/integration
mkdir -p tests/performance
mkdir -p docs/api
```

#### 1.3 Enhanced Requirements
```bash
# Update requirements.txt with new dependencies
cat >> requirements.txt << EOF

# New Platform Support
twitch-python>=0.2.0
tiktok-downloader>=1.0.0
vimeo-downloader>=0.1.0

# Database
asyncpg>=0.29.0
alembic>=1.13.0
sqlalchemy[asyncio]>=2.0.23

# AI/ML
transformers>=4.35.0
torch>=2.1.0
scikit-learn>=1.3.0
opencv-python>=4.8.0

# Monitoring
prometheus-client>=0.19.0
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0

# Enhanced Security
cryptography>=41.0.0
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
authlib>=1.2.1

# Performance
asyncio-throttle>=1.0.2
aiocache>=0.12.2
aiofiles>=23.2.1
```

### Step 2: Implement Platform Architecture

#### 2.1 Create Base Platform Processor
```python
# app/platforms/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models import VideoInfo, VideoFormat, DownloadOptions

class BasePlatformProcessor(ABC):
    """Base class for all platform processors."""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform identifier."""
        pass
    
    @property
    @abstractmethod
    def supported_domains(self) -> List[str]:
        """List of supported domain names."""
        pass
    
    @abstractmethod
    async def extract_info(self, url: str) -> VideoInfo:
        """Extract video information."""
        pass
    
    @abstractmethod
    async def get_download_formats(self, url: str) -> List[VideoFormat]:
        """Get available download formats."""
        pass
    
    @abstractmethod
    async def download(self, url: str, options: DownloadOptions) -> str:
        """Download video and return file path."""
        pass
    
    @abstractmethod
    async def get_stream_url(self, url: str, quality: str = "highest") -> str:
        """Get direct stream URL."""
        pass
    
    async def validate_url(self, url: str) -> bool:
        """Validate if URL is supported by this platform."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in self.supported_domains)
```

#### 2.2 Create Platform Registry
```python
# app/platforms/registry.py
from typing import Dict, Type, Optional
from urllib.parse import urlparse
from app.platforms.base import BasePlatformProcessor
from app.platforms.youtube import YouTubeProcessor
from app.platforms.bilibili import BiliBiliProcessor
from app.platforms.twitch import TwitchProcessor
from app.platforms.tiktok import TikTokProcessor
from app.exceptions import UnsupportedURLError

class PlatformRegistry:
    """Registry for managing platform processors."""
    
    def __init__(self):
        self._processors: Dict[str, BasePlatformProcessor] = {}
        self._domain_mapping: Dict[str, str] = {}
        self._register_default_platforms()
    
    def _register_default_platforms(self):
        """Register default platform processors."""
        processors = [
            YouTubeProcessor(),
            BiliBiliProcessor(),
            TwitchProcessor(),
            TikTokProcessor(),
        ]
        
        for processor in processors:
            self.register(processor)
    
    def register(self, processor: BasePlatformProcessor):
        """Register a new platform processor."""
        self._processors[processor.platform_name] = processor
        
        # Map domains to platform names
        for domain in processor.supported_domains:
            self._domain_mapping[domain] = processor.platform_name
    
    def detect_platform(self, url: str) -> str:
        """Detect platform from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check exact match first
        if domain in self._domain_mapping:
            return self._domain_mapping[domain]
        
        # Check partial matches
        for registered_domain, platform in self._domain_mapping.items():
            if registered_domain in domain:
                return platform
        
        raise UnsupportedURLError(f"Unsupported URL: {url}")
    
    def get_processor(self, platform_name: str) -> BasePlatformProcessor:
        """Get processor by platform name."""
        if platform_name not in self._processors:
            raise UnsupportedURLError(f"Platform not supported: {platform_name}")
        return self._processors[platform_name]
    
    def get_processor_for_url(self, url: str) -> BasePlatformProcessor:
        """Get processor for URL."""
        platform = self.detect_platform(url)
        return self.get_processor(platform)
    
    def list_platforms(self) -> List[str]:
        """List all registered platforms."""
        return list(self._processors.keys())

# Global registry instance
platform_registry = PlatformRegistry()
```

#### 2.3 Implement Twitch Processor
```python
# app/platforms/twitch.py
from typing import List, Dict, Any
import aiohttp
from app.platforms.base import BasePlatformProcessor
from app.models import VideoInfo, VideoFormat, DownloadOptions
from app.config import settings

class TwitchProcessor(BasePlatformProcessor):
    """Twitch platform processor for clips and VODs."""
    
    @property
    def platform_name(self) -> str:
        return "twitch"
    
    @property
    def supported_domains(self) -> List[str]:
        return ["twitch.tv", "www.twitch.tv", "clips.twitch.tv"]
    
    def __init__(self):
        self.client_id = settings.twitch_client_id
        self.client_secret = settings.twitch_client_secret
        self._access_token = None
    
    async def _get_access_token(self) -> str:
        """Get Twitch API access token."""
        if self._access_token:
            return self._access_token
        
        async with aiohttp.ClientSession() as session:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            
            async with session.post('https://id.twitch.tv/oauth2/token', data=data) as response:
                token_data = await response.json()
                self._access_token = token_data['access_token']
                return self._access_token
    
    async def extract_info(self, url: str) -> VideoInfo:
        """Extract Twitch video information."""
        video_id = self._extract_video_id(url)
        access_token = await self._get_access_token()
        
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {access_token}'
        }
        
        async with aiohttp.ClientSession() as session:
            # Determine if it's a clip or VOD
            if 'clips.twitch.tv' in url or '/clip/' in url:
                api_url = f'https://api.twitch.tv/helix/clips?id={video_id}'
            else:
                api_url = f'https://api.twitch.tv/helix/videos?id={video_id}'
            
            async with session.get(api_url, headers=headers) as response:
                data = await response.json()
                
                if not data.get('data'):
                    raise VideoNotFoundError(f"Twitch video not found: {video_id}")
                
                video_data = data['data'][0]
                
                return VideoInfo(
                    id=video_data['id'],
                    title=video_data.get('title', 'Untitled'),
                    description=video_data.get('description', ''),
                    duration=self._parse_duration(video_data.get('duration')),
                    uploader=video_data.get('user_name', 'Unknown'),
                    upload_date=video_data.get('created_at', ''),
                    view_count=video_data.get('view_count', 0),
                    thumbnail=video_data.get('thumbnail_url', ''),
                    platform="twitch"
                )
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from Twitch URL."""
        import re
        
        # Clip URL patterns
        clip_patterns = [
            r'clips\.twitch\.tv/([^/?]+)',
            r'twitch\.tv/\w+/clip/([^/?]+)',
        ]
        
        # VOD URL patterns
        vod_patterns = [
            r'twitch\.tv/videos/(\d+)',
        ]
        
        for pattern in clip_patterns + vod_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """Parse Twitch duration string to seconds."""
        if not duration_str:
            return None
        
        # Handle different duration formats
        # e.g., "1h23m45s" or "3m30s"
        import re
        
        hours = re.search(r'(\d+)h', duration_str)
        minutes = re.search(r'(\d+)m', duration_str)
        seconds = re.search(r'(\d+)s', duration_str)
        
        total_seconds = 0
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
        
        return total_seconds if total_seconds > 0 else None
    
    async def get_download_formats(self, url: str) -> List[VideoFormat]:
        """Get available download formats for Twitch video."""
        # Twitch typically provides limited format options
        return [
            VideoFormat(format_id="mp4", ext="mp4", quality="source"),
            VideoFormat(format_id="mp4_720", ext="mp4", quality="720p"),
            VideoFormat(format_id="mp4_480", ext="mp4", quality="480p"),
        ]
    
    async def download(self, url: str, options: DownloadOptions) -> str:
        """Download Twitch video."""
        # Implementation would use streamlink or similar tool
        # for actual Twitch video downloading
        pass
    
    async def get_stream_url(self, url: str, quality: str = "highest") -> str:
        """Get direct stream URL for Twitch video."""
        # Implementation would use Twitch API to get playback URLs
        pass
```

### Step 3: Database Integration

#### 3.1 Set Up Database Schema
```python
# app/database/models.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime)
    
    # Relationships
    download_tasks = relationship("DownloadTask", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2048), nullable=False)
    platform = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    title = Column(String(500))
    description = Column(Text)
    duration = Column(Integer)
    uploader = Column(String(255))
    upload_date = Column(DateTime)
    view_count = Column(Integer)
    like_count = Column(Integer)
    thumbnail_url = Column(String(2048))
    metadata = Column(JSONB)
    created_at = Column(DateTime, nullable=False)
    
    # Relationships
    download_tasks = relationship("DownloadTask", back_populates="video")

class DownloadTask(Base):
    __tablename__ = "download_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    quality = Column(String(50))
    format = Column(String(50))
    audio_only = Column(Boolean, default=False)
    progress = Column(DECIMAL(5, 2), default=0)
    file_path = Column(String(1024))
    file_size = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="download_tasks")
    video = relationship("Video", back_populates="download_tasks")
```

#### 3.2 Database Migrations
```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create enum types
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'user', 'guest')")
    op.execute("CREATE TYPE video_platform AS ENUM ('youtube', 'bilibili', 'twitch', 'tiktok', 'vimeo')")
    op.execute("CREATE TYPE task_status AS ENUM ('queued', 'processing', 'completed', 'failed', 'cancelled')")
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'user', 'guest', name='user_role'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_active', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create videos table
    op.create_table('videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('platform', postgresql.ENUM('youtube', 'bilibili', 'twitch', 'tiktok', 'vimeo', name='video_platform'), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('uploader', sa.String(length=255), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=2048), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', 'platform', name='uq_video_url_platform')
    )
    
    # Create download_tasks table
    op.create_table('download_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('queued', 'processing', 'completed', 'failed', 'cancelled', name='task_status'), nullable=False),
        sa.Column('quality', sa.String(length=50), nullable=True),
        sa.Column('format', sa.String(length=50), nullable=True),
        sa.Column('audio_only', sa.Boolean(), nullable=True),
        sa.Column('progress', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('file_path', sa.String(length=1024), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_download_tasks_user_id', 'download_tasks', ['user_id'])
    op.create_index('idx_download_tasks_status', 'download_tasks', ['status'])
    op.create_index('idx_videos_platform', 'videos', ['platform'])
    op.create_index('idx_videos_external_id', 'videos', ['external_id'])

def downgrade():
    op.drop_index('idx_videos_external_id')
    op.drop_index('idx_videos_platform')
    op.drop_index('idx_download_tasks_status')
    op.drop_index('idx_download_tasks_user_id')
    op.drop_table('download_tasks')
    op.drop_table('videos')
    op.drop_table('users')
    op.execute("DROP TYPE task_status")
    op.execute("DROP TYPE video_platform")
    op.execute("DROP TYPE user_role")
```

### Step 4: Enhanced Configuration

#### 4.1 Configuration with Platform Support
```python
# app/config.py (Enhanced)
import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, validator

class PlatformConfig(BaseSettings):
    """Platform-specific configuration."""
    enabled: bool = True
    rate_limit: int = 100
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    max_quality: str = "highest"
    features: Dict[str, bool] = {}

class Settings(BaseSettings):
    """Enhanced application settings."""
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://user:pass@localhost/ytbhelper"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Platform Configurations
    platforms: Dict[str, PlatformConfig] = {
        "youtube": PlatformConfig(
            enabled=True,
            rate_limit=100,
            features={"live_streams": True, "playlists": True}
        ),
        "bilibili": PlatformConfig(
            enabled=True,
            rate_limit=50,
            features={"subtitles": True, "chapters": True}
        ),
        "twitch": PlatformConfig(
            enabled=True,
            rate_limit=75,
            api_key=os.getenv("TWITCH_CLIENT_ID"),
            api_secret=os.getenv("TWITCH_CLIENT_SECRET"),
            features={"clips": True, "vods": True}
        ),
        "tiktok": PlatformConfig(
            enabled=False,  # Disabled by default due to complexity
            rate_limit=30,
            features={"watermark_removal": True}
        )
    }
    
    # AI/ML Configuration
    ai_enabled: bool = False
    ai_model_path: str = "models/"
    content_classification_enabled: bool = False
    duplicate_detection_enabled: bool = False
    
    # Enhanced Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    bcrypt_rounds: int = 12
    
    # Performance Settings
    max_concurrent_downloads_per_user: int = 3
    global_download_worker_count: int = 10
    download_timeout_minutes: int = 30
    
    # Feature Flags
    feature_flags: Dict[str, bool] = {
        "web_dashboard": True,
        "mobile_app": False,
        "browser_extensions": False,
        "analytics": True,
        "webhooks": False,
        "scheduled_downloads": False
    }
    
    class Config:
        env_prefix = ""
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

### Step 5: Testing Framework

#### 5.1 Enhanced Test Structure
```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.models import Base
from app.config import settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/ytbhelper_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session

@pytest.fixture
async def test_client():
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Platform-specific test fixtures
@pytest.fixture
def sample_youtube_url():
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

@pytest.fixture
def sample_twitch_url():
    return "https://www.twitch.tv/videos/123456789"

@pytest.fixture
def sample_video_info():
    from app.models import VideoInfo
    return VideoInfo(
        id="test123",
        title="Test Video",
        description="Test Description",
        duration=180,
        uploader="Test Channel",
        platform="youtube"
    )
```

#### 5.2 Platform Integration Tests
```python
# tests/test_platforms.py
import pytest
from app.platforms.registry import platform_registry
from app.exceptions import UnsupportedURLError

class TestPlatformRegistry:
    """Test platform registry functionality."""
    
    def test_detect_youtube_platform(self, sample_youtube_url):
        platform = platform_registry.detect_platform(sample_youtube_url)
        assert platform == "youtube"
    
    def test_detect_twitch_platform(self, sample_twitch_url):
        platform = platform_registry.detect_platform(sample_twitch_url)
        assert platform == "twitch"
    
    def test_unsupported_url_raises_exception(self):
        with pytest.raises(UnsupportedURLError):
            platform_registry.detect_platform("https://unsupported.com/video")
    
    def test_get_processor_for_platform(self):
        processor = platform_registry.get_processor("youtube")
        assert processor.platform_name == "youtube"
    
    def test_list_platforms(self):
        platforms = platform_registry.list_platforms()
        assert "youtube" in platforms
        assert "bilibili" in platforms
        assert "twitch" in platforms

@pytest.mark.asyncio
class TestPlatformProcessors:
    """Test individual platform processors."""
    
    async def test_youtube_processor_extract_info(self, sample_youtube_url):
        processor = platform_registry.get_processor("youtube")
        video_info = await processor.extract_info(sample_youtube_url)
        
        assert video_info.id is not None
        assert video_info.title is not None
        assert video_info.platform == "youtube"
    
    async def test_platform_processor_validation(self, sample_youtube_url):
        processor = platform_registry.get_processor("youtube")
        is_valid = await processor.validate_url(sample_youtube_url)
        assert is_valid is True
        
        is_invalid = await processor.validate_url("https://invalid.com/video")
        assert is_invalid is False
```

## 📊 Monitoring Implementation

### Performance Metrics
```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools

# Metrics definitions
download_requests_total = Counter(
    'download_requests_total',
    'Total download requests',
    ['platform', 'status', 'user_tier']
)

download_duration = Histogram(
    'download_duration_seconds',
    'Download duration in seconds',
    ['platform', 'quality']
)

active_downloads = Gauge(
    'active_downloads',
    'Currently active downloads'
)

platform_api_calls = Counter(
    'platform_api_calls_total',
    'Total API calls to platforms',
    ['platform', 'endpoint', 'status']
)

def track_download_metrics(platform: str):
    """Decorator to track download metrics."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            active_downloads.inc()
            
            try:
                result = await func(*args, **kwargs)
                download_requests_total.labels(
                    platform=platform,
                    status='success',
                    user_tier='free'  # TODO: Get from user context
                ).inc()
                return result
            except Exception as e:
                download_requests_total.labels(
                    platform=platform,
                    status='error',
                    user_tier='free'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                download_duration.labels(
                    platform=platform,
                    quality='unknown'  # TODO: Get from request
                ).observe(duration)
                active_downloads.dec()
        
        return wrapper
    return decorator

# Start metrics server
def start_metrics_server(port: int = 8090):
    """Start Prometheus metrics server."""
    start_http_server(port)
```

## 🚀 Deployment Scripts

### Docker Compose for Development
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://ytbhelper:password@postgres:5432/ytbhelper
      - REDIS_HOST=redis
      - ENVIRONMENT=development
    volumes:
      - ./app:/app/app
      - ./downloads:/app/downloads
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_USER=ytbhelper
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=ytbhelper
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@example.com
      - PGADMIN_DEFAULT_PASSWORD=admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
  redis_data:
```

### Development Setup Script
```bash
#!/bin/bash
# scripts/setup-dev.sh

set -e

echo "🚀 Setting up YouTuberBilBiliHelper development environment..."

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed."; exit 1; }

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pip install pre-commit
pre-commit install

# Create environment file
echo "⚙️ Creating environment configuration..."
cp .env.example .env
echo "Please edit .env file with your configuration"

# Start infrastructure services
echo "🐳 Starting infrastructure services..."
docker-compose -f docker-compose.dev.yml up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Install frontend dependencies
echo "🎨 Setting up frontend development environment..."
cd frontend
npm install
cd ..

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run 'source venv/bin/activate' to activate Python environment"
echo "3. Run 'python main.py' to start the API server"
echo "4. Run 'cd frontend && npm start' to start the frontend development server"
echo "5. Visit http://localhost:8000/docs for API documentation"
```

## 🎯 Next Implementation Steps

1. **Week 1-2**: Complete platform architecture and Twitch integration
2. **Week 3-4**: Add TikTok and Vimeo support, enhance testing
3. **Week 5-6**: Database integration and migration system
4. **Week 7-8**: Enhanced monitoring and production readiness

This implementation guide provides the foundation for systematically building out the enhanced YouTuberBilBiliHelper platform according to the improvement plan and roadmap.
