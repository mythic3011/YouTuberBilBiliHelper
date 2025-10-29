"""Unit tests for cache utility module."""

import pytest
from app.utils.cache import (
    generate_cache_key,
    hash_cache_key,
    generate_video_cache_key,
    generate_stream_cache_key,
    generate_auth_cache_key,
    serialize_for_cache,
    deserialize_from_cache
)


class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""
    
    def test_simple_key(self):
        key = generate_cache_key("prefix")
        assert key == "prefix"
    
    def test_key_with_args(self):
        key = generate_cache_key("prefix", "arg1", "arg2")
        assert key == "prefix:arg1:arg2"
    
    def test_key_with_kwargs(self):
        key = generate_cache_key("prefix", quality="720p", format="mp4")
        assert "prefix" in key
        assert "quality=720p" in key
        assert "format=mp4" in key
    
    def test_key_with_args_and_kwargs(self):
        key = generate_cache_key("video", "youtube", "abc123", quality="best")
        assert key == "video:youtube:abc123:quality=best"
    
    def test_kwargs_sorted(self):
        key1 = generate_cache_key("prefix", a="1", b="2", c="3")
        key2 = generate_cache_key("prefix", c="3", b="2", a="1")
        assert key1 == key2  # Order should be consistent


class TestHashCacheKey:
    """Tests for hash_cache_key function."""
    
    def test_hash_produces_consistent_output(self):
        key = "video:youtube:abc123:quality=best"
        hash1 = hash_cache_key(key)
        hash2 = hash_cache_key(key)
        assert hash1 == hash2
    
    def test_hash_produces_different_output_for_different_keys(self):
        hash1 = hash_cache_key("key1")
        hash2 = hash_cache_key("key2")
        assert hash1 != hash2
    
    def test_hash_length(self):
        hash_result = hash_cache_key("test")
        assert len(hash_result) == 64  # SHA256 produces 64 hex characters


class TestGenerateVideoCacheKey:
    """Tests for generate_video_cache_key function."""
    
    def test_basic_video_key(self):
        key = generate_video_cache_key("youtube", "abc123")
        assert "video" in key
        assert "youtube" in key
        assert "abc123" in key
    
    def test_video_key_with_quality(self):
        key = generate_video_cache_key("youtube", "abc123", quality="720p")
        assert "quality=720p" in key
    
    def test_video_key_with_format(self):
        key = generate_video_cache_key("youtube", "abc123", format="mp4")
        assert "format=mp4" in key
    
    def test_video_key_defaults(self):
        key = generate_video_cache_key("youtube", "abc123")
        assert "quality=best" in key
        assert "format=any" in key


class TestGenerateStreamCacheKey:
    """Tests for generate_stream_cache_key function."""
    
    def test_basic_stream_key(self):
        key = generate_stream_cache_key("youtube", "abc123")
        assert "stream" in key
        assert "youtube" in key
        assert "abc123" in key
    
    def test_stream_key_with_quality(self):
        key = generate_stream_cache_key("youtube", "abc123", quality="1080p")
        assert "quality=1080p" in key
    
    def test_stream_key_default_quality(self):
        key = generate_stream_cache_key("youtube", "abc123")
        assert "quality=best" in key


class TestGenerateAuthCacheKey:
    """Tests for generate_auth_cache_key function."""
    
    def test_auth_cache_key(self):
        key = generate_auth_cache_key("youtube")
        assert key == "auth:youtube"
    
    def test_auth_cache_key_different_platforms(self):
        key1 = generate_auth_cache_key("youtube")
        key2 = generate_auth_cache_key("bilibili")
        assert key1 != key2


class TestSerializeForCache:
    """Tests for serialize_for_cache function."""
    
    def test_serialize_dict(self):
        data = {"key": "value", "number": 42}
        serialized = serialize_for_cache(data)
        assert isinstance(serialized, str)
        assert "key" in serialized
        assert "value" in serialized
    
    def test_serialize_list(self):
        data = [1, 2, 3, "four"]
        serialized = serialize_for_cache(data)
        assert isinstance(serialized, str)
        assert "1" in serialized
        assert "four" in serialized
    
    def test_serialize_string(self):
        data = "simple string"
        serialized = serialize_for_cache(data)
        assert isinstance(serialized, str)
        assert data in serialized
    
    def test_serialize_with_unicode(self):
        data = {"title": "视频标题", "emoji": "🎉"}
        serialized = serialize_for_cache(data)
        assert "视频标题" in serialized
        assert "🎉" in serialized
    
    def test_serialize_non_serializable_raises_error(self):
        with pytest.raises(ValueError):
            serialize_for_cache(object())


class TestDeserializeFromCache:
    """Tests for deserialize_from_cache function."""
    
    def test_deserialize_dict(self):
        original = {"key": "value", "number": 42}
        serialized = serialize_for_cache(original)
        deserialized = deserialize_from_cache(serialized)
        assert deserialized == original
    
    def test_deserialize_list(self):
        original = [1, 2, 3, "four"]
        serialized = serialize_for_cache(original)
        deserialized = deserialize_from_cache(serialized)
        assert deserialized == original
    
    def test_deserialize_string(self):
        original = "simple string"
        serialized = serialize_for_cache(original)
        deserialized = deserialize_from_cache(serialized)
        assert deserialized == original
    
    def test_deserialize_invalid_json_raises_error(self):
        with pytest.raises(ValueError):
            deserialize_from_cache("not valid json{]")
    
    def test_roundtrip_complex_data(self):
        original = {
            "title": "Video Title",
            "duration": 120,
            "formats": [
                {"quality": "720p", "size": 1024},
                {"quality": "1080p", "size": 2048}
            ],
            "metadata": {
                "views": 1000,
                "likes": 50
            }
        }
        serialized = serialize_for_cache(original)
        deserialized = deserialize_from_cache(serialized)
        assert deserialized == original

