"""Configuration settings for the YouTuberBilBiliHelper API."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Rate Limiting
    rate_limit_window: int = 60  # seconds
    rate_limit_max_requests: int = 100
    
    # Storage Configuration
    download_directory: str = "downloads"
    max_storage_gb: int = 10
    temp_file_retention_hours: int = 24
    
    # API Configuration
    api_title: str = "YouTuberBilBiliHelper API"
    api_version: str = "2.0.0"
    api_description: str = "Enhanced API for YouTube and BiliBili video processing"
    cors_origins: list = ["*"]
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    # Download Configuration
    max_video_duration_minutes: int = 60
    allowed_video_formats: list = ["mp4", "webm", "mkv"]
    max_concurrent_downloads: int = 5
    
    # Security
    enable_rate_limiting: bool = True
    enable_storage_limits: bool = True
    
    # Performance & Caching
    cleanup_interval: int = 3600  # seconds (1 hour)
    cache_max_age: int = 1800  # seconds (30 minutes)
    stream_cache_ttl: int = 3600  # seconds (1 hour)
    stream_chunk_size: int = 8192  # bytes
    
    # Platform-specific cache TTLs
    youtube_cache_ttl: int = 1800  # 30 minutes (URLs expire faster)
    bilibili_cache_ttl: int = 3600  # 1 hour
    twitch_cache_ttl: int = 1800  # 30 minutes
    instagram_cache_ttl: int = 900  # 15 minutes (more volatile)
    twitter_cache_ttl: int = 900  # 15 minutes (more volatile)
    
    @field_validator('max_storage_gb')
    @classmethod
    def validate_storage_limit(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Storage limit must be positive')
        return v
    
    @field_validator('rate_limit_max_requests')
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Rate limit must be positive')
        return v
    
    @property
    def max_storage_bytes(self) -> int:
        """Convert GB to bytes."""
        return self.max_storage_gb * 1024 * 1024 * 1024
    
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_prefix = ""
        env_file = ".env"


# Global settings instance
settings = Settings()
