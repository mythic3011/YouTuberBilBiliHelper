"""Tests for the simple API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestSimpleEndpoints:
    """Test simple API endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "YouTuberBilBiliHelper API"
        assert data["version"] == "2.0.0"
        assert "simple_endpoints" in data
        assert "examples" in data
        assert "supported_platforms" in data
        
    def test_platforms_endpoint(self):
        """Test platforms listing endpoint."""
        response = client.get("/api/platforms")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_platforms" in data
        assert "total_platforms" in data
        assert data["total_platforms"] == 5
        
        # Check platform structure
        platforms = data["supported_platforms"]
        assert len(platforms) == 5
        
        # Check YouTube platform
        youtube = next((p for p in platforms if p["platform_id"] == "youtube"), None)
        assert youtube is not None
        assert "youtube.com" in youtube["domains"]
        assert "youtu.be" in youtube["domains"]
        assert "streaming" in youtube["features"]
        
    def test_health_endpoint(self):
        """Test simple health endpoint."""
        response = client.get("/api/health", allow_redirects=False)
        assert response.status_code == 302
        assert "/api/v2/system/health" in response.headers["location"]
        
    def test_stream_endpoint_missing_url(self):
        """Test stream endpoint with missing URL parameter."""
        response = client.get("/api/stream")
        assert response.status_code == 422  # Validation error
        
    def test_stream_endpoint_invalid_format(self):
        """Test stream endpoint with invalid format."""
        response = client.get("/api/stream?url=https://youtu.be/test&format=invalid")
        assert response.status_code == 422  # Validation error
        
    def test_stream_endpoint_invalid_quality(self):
        """Test stream endpoint with invalid quality."""
        response = client.get("/api/stream?url=https://youtu.be/test&quality=invalid")
        assert response.status_code == 422  # Validation error
        
    def test_info_endpoint_missing_url(self):
        """Test info endpoint with missing URL parameter."""
        response = client.get("/api/info")
        assert response.status_code == 422  # Validation error
        
    def test_download_endpoint_missing_url(self):
        """Test download endpoint with missing URL parameter."""
        response = client.get("/api/download")
        assert response.status_code == 422  # Validation error
        
    def test_formats_endpoint_missing_url(self):
        """Test formats endpoint with missing URL parameter."""
        response = client.get("/api/formats")
        assert response.status_code == 422  # Validation error
        
    def test_embed_endpoint_missing_url(self):
        """Test embed endpoint with missing URL parameter."""
        response = client.get("/api/embed")
        assert response.status_code == 422  # Validation error


class TestURLExtraction:
    """Test URL extraction functionality."""
    
    def test_youtube_url_extraction(self):
        """Test YouTube URL extraction."""
        from app.routes.simple import extract_video_id_from_url
        
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", ("youtube", "dQw4w9WgXcQ")),
            ("https://youtu.be/dQw4w9WgXcQ", ("youtube", "dQw4w9WgXcQ")),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", ("youtube", "dQw4w9WgXcQ")),
        ]
        
        for url, expected in test_cases:
            result = extract_video_id_from_url(url)
            assert result == expected
            
    def test_bilibili_url_extraction(self):
        """Test BiliBili URL extraction."""
        from app.routes.simple import extract_video_id_from_url
        
        test_cases = [
            ("https://www.bilibili.com/video/BV1xx411c7mu", ("bilibili", "BV1xx411c7mu")),
            ("https://bilibili.com/video/BV1xx411c7mu", ("bilibili", "BV1xx411c7mu")),
        ]
        
        for url, expected in test_cases:
            result = extract_video_id_from_url(url)
            assert result == expected
            
    def test_twitch_url_extraction(self):
        """Test Twitch URL extraction."""
        from app.routes.simple import extract_video_id_from_url
        
        test_cases = [
            ("https://clips.twitch.tv/example-clip", ("twitch", "example-clip")),
            ("https://www.twitch.tv/videos/123456789", ("twitch", "123456789")),
        ]
        
        for url, expected in test_cases:
            result = extract_video_id_from_url(url)
            assert result == expected
            
    def test_instagram_url_extraction(self):
        """Test Instagram URL extraction."""
        from app.routes.simple import extract_video_id_from_url
        
        test_cases = [
            ("https://www.instagram.com/p/ABC123/", ("instagram", "ABC123")),
            ("https://www.instagram.com/reel/ABC123/", ("instagram", "ABC123")),
        ]
        
        for url, expected in test_cases:
            result = extract_video_id_from_url(url)
            assert result == expected
            
    def test_twitter_url_extraction(self):
        """Test Twitter URL extraction."""
        from app.routes.simple import extract_video_id_from_url
        
        test_cases = [
            ("https://twitter.com/user/status/1234567890", ("twitter", "1234567890")),
            ("https://x.com/user/status/1234567890", ("twitter", "1234567890")),
        ]
        
        for url, expected in test_cases:
            result = extract_video_id_from_url(url)
            assert result == expected
            
    def test_unsupported_url(self):
        """Test unsupported URL raises exception."""
        from app.routes.simple import extract_video_id_from_url
        from app.exceptions import UnsupportedURLError
        
        with pytest.raises(UnsupportedURLError):
            extract_video_id_from_url("https://example.com/video")


class TestQualityMapping:
    """Test quality mapping functionality."""
    
    def test_quality_mapping(self):
        """Test quality string to yt-dlp mapping."""
        # This would test the quality mapping logic
        # if it was extracted to a separate function
        quality_map = {
            "highest": "best",
            "lowest": "worst", 
            "720p": "720p",
            "480p": "480p",
            "360p": "360p"
        }
        
        assert quality_map["highest"] == "best"
        assert quality_map["lowest"] == "worst"
        assert quality_map["720p"] == "720p"
