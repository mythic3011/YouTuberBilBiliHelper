"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError
from app.models import (
    VideoInfo, DownloadRequest, StreamRequest, BatchDownloadRequest,
    VideoQuality, VideoFormat
)


class TestVideoInfo:
    """Test VideoInfo model."""
    
    def test_valid_video_info(self):
        """Test creating valid video info."""
        video_info = VideoInfo(
            id="dQw4w9WgXcQ",
            title="Rick Astley - Never Gonna Give You Up",
            description="The official video",
            duration=213.0,
            uploader="Rick Astley",
            upload_date="2009-10-25",
            view_count=1000000000,
            like_count=10000000,
            thumbnail="https://example.com/thumb.jpg"
        )
        
        assert video_info.id == "dQw4w9WgXcQ"
        assert video_info.title == "Rick Astley - Never Gonna Give You Up"
        assert video_info.duration == 213.0
        assert isinstance(video_info.duration, float)
        
    def test_minimal_video_info(self):
        """Test creating video info with minimal required fields."""
        video_info = VideoInfo(
            id="test123",
            title="Test Video"
        )
        
        assert video_info.id == "test123"
        assert video_info.title == "Test Video"
        assert video_info.description is None
        assert video_info.duration is None
        
    def test_duration_as_float(self):
        """Test that duration accepts float values."""
        video_info = VideoInfo(
            id="test123",
            title="Test Video",
            duration=123.45
        )
        
        assert video_info.duration == 123.45
        assert isinstance(video_info.duration, float)


class TestDownloadRequest:
    """Test DownloadRequest model."""
    
    def test_valid_youtube_url(self):
        """Test valid YouTube URL."""
        request = DownloadRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert request.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert request.quality == VideoQuality.HIGHEST
        assert request.format == VideoFormat.MP4
        
    def test_valid_bilibili_url(self):
        """Test valid BiliBili URL."""
        request = DownloadRequest(url="https://www.bilibili.com/video/BV1xx411c7mu")
        assert request.url == "https://www.bilibili.com/video/BV1xx411c7mu"
        
    def test_custom_quality_and_format(self):
        """Test custom quality and format."""
        request = DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            quality=VideoQuality.MEDIUM,
            format=VideoFormat.WEBM
        )
        
        assert request.quality == VideoQuality.MEDIUM
        assert request.format == VideoFormat.WEBM
        
    def test_audio_only_option(self):
        """Test audio only download."""
        request = DownloadRequest(
            url="https://www.youtube.com/watch?v=test",
            audio_only=True
        )
        
        assert request.audio_only is True
        
    def test_url_validation_youtube(self):
        """Test URL validation for YouTube."""
        # Valid YouTube URLs should pass
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ", 
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in valid_urls:
            request = DownloadRequest(url=url)
            assert request.url == url
            
    def test_url_validation_bilibili(self):
        """Test URL validation for BiliBili."""
        # Valid BiliBili URLs should pass
        valid_urls = [
            "https://www.bilibili.com/video/BV1xx411c7mu",
            "https://bilibili.com/video/BV1xx411c7mu",
            "https://b23.tv/abc123"
        ]
        
        for url in valid_urls:
            request = DownloadRequest(url=url)
            assert request.url == url


class TestStreamRequest:
    """Test StreamRequest model."""
    
    def test_valid_stream_request(self):
        """Test valid stream request."""
        request = StreamRequest(url="https://www.youtube.com/watch?v=test")
        assert request.url == "https://www.youtube.com/watch?v=test"
        assert request.quality == VideoQuality.HIGHEST
        
    def test_stream_request_with_quality(self):
        """Test stream request with specific quality."""
        request = StreamRequest(
            url="https://www.youtube.com/watch?v=test",
            quality=VideoQuality.LOW
        )
        assert request.quality == VideoQuality.LOW


class TestBatchDownloadRequest:
    """Test BatchDownloadRequest model."""
    
    def test_valid_batch_request(self):
        """Test valid batch request."""
        urls = [
            "https://www.youtube.com/watch?v=test1",
            "https://www.youtube.com/watch?v=test2"
        ]
        
        request = BatchDownloadRequest(urls=urls)
        assert len(request.urls) == 2
        assert request.quality == VideoQuality.HIGHEST
        
    def test_batch_size_limit(self):
        """Test batch size limit validation."""
        # Create 11 URLs (over the limit of 10)
        urls = [f"https://www.youtube.com/watch?v=test{i}" for i in range(11)]
        
        with pytest.raises(ValidationError) as exc_info:
            BatchDownloadRequest(urls=urls)
            
        assert "Maximum 10 URLs allowed per batch" in str(exc_info.value)
        
    def test_empty_batch(self):
        """Test empty batch request."""
        with pytest.raises(ValidationError):
            BatchDownloadRequest(urls=[])
            
    def test_batch_with_quality(self):
        """Test batch request with specific quality."""
        urls = ["https://www.youtube.com/watch?v=test1"]
        request = BatchDownloadRequest(urls=urls, quality=VideoQuality.MEDIUM)
        
        assert request.quality == VideoQuality.MEDIUM


class TestEnums:
    """Test enum values."""
    
    def test_video_quality_enum(self):
        """Test VideoQuality enum values."""
        assert VideoQuality.HIGHEST == "highest"
        assert VideoQuality.HIGH == "high"
        assert VideoQuality.MEDIUM == "medium"
        assert VideoQuality.LOW == "low"
        assert VideoQuality.LOWEST == "lowest"
        assert VideoQuality.BEST_AUDIO == "best_audio"
        assert VideoQuality.BEST_VIDEO == "best_video"
        
    def test_video_format_enum(self):
        """Test VideoFormat enum values."""
        assert VideoFormat.MP4 == "mp4"
        assert VideoFormat.WEBM == "webm"
        assert VideoFormat.MKV == "mkv"
        assert VideoFormat.MP3 == "mp3"
        assert VideoFormat.M4A == "m4a"
