"""Tests for configuration management."""

import pytest
from pydantic import ValidationError
from app.config import Settings


class TestSettings:
    """Test configuration settings."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        assert settings.api_title == "YouTuberBilBiliHelper API"
        assert settings.api_version == "2.0.0"
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.max_storage_gb == 10.0
        assert settings.rate_limit_max_requests == 100
        assert settings.rate_limit_window == 60
        
    def test_cache_ttl_settings(self):
        """Test cache TTL configuration."""
        settings = Settings()
        
        assert settings.cleanup_interval == 3600
        assert settings.cache_max_age == 1800
        assert settings.stream_cache_ttl == 3600
        assert settings.stream_chunk_size == 8192
        
    def test_platform_specific_ttls(self):
        """Test platform-specific cache TTLs."""
        settings = Settings()
        
        assert settings.youtube_cache_ttl == 1800
        assert settings.bilibili_cache_ttl == 3600
        assert settings.twitch_cache_ttl == 1800
        assert settings.instagram_cache_ttl == 900
        assert settings.twitter_cache_ttl == 900
        
    def test_storage_limit_validation(self):
        """Test storage limit validation."""
        # Valid storage limit
        settings = Settings(max_storage_gb=5.0)
        assert settings.max_storage_gb == 5.0
        
        # Invalid storage limit
        with pytest.raises(ValidationError):
            Settings(max_storage_gb=0)
            
        with pytest.raises(ValidationError):
            Settings(max_storage_gb=-1)
            
    def test_rate_limit_validation(self):
        """Test rate limit validation."""
        # Valid rate limit
        settings = Settings(rate_limit_max_requests=50)
        assert settings.rate_limit_max_requests == 50
        
        # Invalid rate limit
        with pytest.raises(ValidationError):
            Settings(rate_limit_max_requests=0)
            
        with pytest.raises(ValidationError):
            Settings(rate_limit_max_requests=-1)
            
    def test_max_storage_bytes_property(self):
        """Test storage bytes conversion."""
        settings = Settings(max_storage_gb=2.0)
        expected_bytes = 2.0 * 1024 * 1024 * 1024  # 2GB in bytes
        assert settings.max_storage_bytes == expected_bytes
        
    def test_cors_origins_default(self):
        """Test default CORS origins."""
        settings = Settings()
        assert "*" in settings.cors_origins
        
    def test_allowed_formats(self):
        """Test allowed video formats."""
        settings = Settings()
        expected_formats = ["mp4", "webm", "mkv"]
        assert settings.allowed_video_formats == expected_formats
        
    def test_security_settings(self):
        """Test security-related settings."""
        settings = Settings()
        assert settings.enable_rate_limiting is True
        assert settings.enable_storage_limits is True
        
    def test_temp_file_retention(self):
        """Test temporary file retention settings."""
        settings = Settings()
        assert settings.temp_file_retention_hours == 24
        assert isinstance(settings.temp_file_retention_hours, int)
        
    def test_max_video_duration(self):
        """Test maximum video duration setting."""
        settings = Settings()
        assert settings.max_video_duration_minutes == 60
        assert isinstance(settings.max_video_duration_minutes, int)
