"""Unit tests for validators utility module."""

import pytest
from app.utils.validators import (
    validate_url,
    extract_video_id,
    validate_platform,
    validate_quality,
    validate_format,
    sanitize_filename,
    validate_video_id,
    validate_pagination
)


class TestValidateURL:
    """Tests for validate_url function."""
    
    def test_valid_http_url(self):
        assert validate_url("http://example.com") is True
    
    def test_valid_https_url(self):
        assert validate_url("https://example.com/path") is True
    
    def test_invalid_url_no_scheme(self):
        assert validate_url("example.com") is False
    
    def test_invalid_url_empty(self):
        assert validate_url("") is False
    
    def test_invalid_url_malformed(self):
        assert validate_url("not a url") is False


class TestExtractVideoID:
    """Tests for extract_video_id function."""
    
    def test_youtube_watch_url(self):
        result = extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == ("youtube", "dQw4w9WgXcQ")
    
    def test_youtube_short_url(self):
        result = extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert result == ("youtube", "dQw4w9WgXcQ")
    
    def test_bilibili_url(self):
        result = extract_video_id("https://www.bilibili.com/video/BV1xx411c7mD")
        assert result == ("bilibili", "BV1xx411c7mD")
    
    def test_twitter_url(self):
        result = extract_video_id("https://twitter.com/user/status/1234567890")
        assert result == ("twitter", "1234567890")
    
    def test_instagram_url(self):
        result = extract_video_id("https://www.instagram.com/p/ABC123xyz/")
        assert result == ("instagram", "ABC123xyz")
    
    def test_unsupported_url(self):
        result = extract_video_id("https://unsupported.com/video/123")
        assert result is None


class TestValidatePlatform:
    """Tests for validate_platform function."""
    
    def test_valid_platforms(self):
        valid = ['youtube', 'bilibili', 'twitter', 'instagram', 'twitch']
        for platform in valid:
            assert validate_platform(platform) is True
    
    def test_case_insensitive(self):
        assert validate_platform("YOUTUBE") is True
        assert validate_platform("YouTube") is True
    
    def test_invalid_platform(self):
        assert validate_platform("invalid") is False
        assert validate_platform("") is False


class TestValidateQuality:
    """Tests for validate_quality function."""
    
    def test_valid_qualities(self):
        valid = ['best', 'worst', '1080p', '720p', '480p', '360p', 'hd', 'sd']
        for quality in valid:
            assert validate_quality(quality) is True
    
    def test_case_insensitive(self):
        assert validate_quality("1080P") is True
        assert validate_quality("HD") is True
    
    def test_invalid_quality(self):
        assert validate_quality("invalid") is False
        assert validate_quality("9999p") is False


class TestValidateFormat:
    """Tests for validate_format function."""
    
    def test_valid_video_formats(self):
        valid = ['mp4', 'webm', 'mkv', 'flv', 'avi']
        for fmt in valid:
            assert validate_format(fmt) is True
    
    def test_valid_audio_formats(self):
        valid = ['mp3', 'm4a', 'wav', 'flac', 'aac']
        for fmt in valid:
            assert validate_format(fmt) is True
    
    def test_invalid_format(self):
        assert validate_format("invalid") is False
        assert validate_format("exe") is False


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""
    
    def test_remove_invalid_characters(self):
        result = sanitize_filename('file:name<with>invalid|chars.mp4')
        assert result == 'filenamewithvalidchars.mp4'
    
    def test_remove_multiple_spaces(self):
        result = sanitize_filename('file    with    spaces.mp4')
        assert result == 'file with spaces.mp4'
    
    def test_trim_whitespace(self):
        result = sanitize_filename('  filename.mp4  ')
        assert result == 'filename.mp4'
    
    def test_truncate_long_filename(self):
        long_name = 'a' * 300 + '.mp4'
        result = sanitize_filename(long_name, max_length=100)
        assert len(result) <= 100
        assert result.endswith('.mp4')
    
    def test_preserve_valid_filename(self):
        valid = 'My_Video-2024.mp4'
        assert sanitize_filename(valid) == valid


class TestValidateVideoID:
    """Tests for validate_video_id function."""
    
    def test_youtube_valid(self):
        assert validate_video_id("dQw4w9WgXcQ", "youtube") is True
    
    def test_youtube_invalid(self):
        assert validate_video_id("tooshort", "youtube") is False
        assert validate_video_id("toolong12345", "youtube") is False
    
    def test_bilibili_bv_valid(self):
        assert validate_video_id("BV1xx411c7mD", "bilibili") is True
    
    def test_bilibili_av_valid(self):
        assert validate_video_id("av12345678", "bilibili") is True
    
    def test_bilibili_invalid(self):
        assert validate_video_id("invalid", "bilibili") is False
    
    def test_twitter_valid(self):
        assert validate_video_id("1234567890", "twitter") is True
    
    def test_twitter_invalid(self):
        assert validate_video_id("not-numbers", "twitter") is False


class TestValidatePagination:
    """Tests for validate_pagination function."""
    
    def test_valid_pagination(self):
        is_valid, error = validate_pagination(1, 20)
        assert is_valid is True
        assert error is None
    
    def test_invalid_page_zero(self):
        is_valid, error = validate_pagination(0, 20)
        assert is_valid is False
        assert "at least 1" in error
    
    def test_invalid_page_negative(self):
        is_valid, error = validate_pagination(-1, 20)
        assert is_valid is False
    
    def test_invalid_page_size_zero(self):
        is_valid, error = validate_pagination(1, 0)
        assert is_valid is False
        assert "at least 1" in error
    
    def test_invalid_page_size_too_large(self):
        is_valid, error = validate_pagination(1, 200, max_page_size=100)
        assert is_valid is False
        assert "cannot exceed" in error
    
    def test_custom_max_page_size(self):
        is_valid, error = validate_pagination(1, 50, max_page_size=50)
        assert is_valid is True
        
        is_valid, error = validate_pagination(1, 51, max_page_size=50)
        assert is_valid is False

