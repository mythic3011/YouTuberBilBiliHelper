"""Tests for service classes."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.redis_service import RedisService
from app.services.streaming_service import StreamingService
from app.exceptions import VideoNotFoundError, ServiceUnavailableError


class TestRedisService:
    """Test Redis service functionality."""
    
    @pytest.fixture
    def redis_service(self):
        """Create Redis service instance."""
        return RedisService()
        
    def test_redis_service_initialization(self, redis_service):
        """Test Redis service initialization."""
        assert redis_service.host == "localhost"
        assert redis_service.port == 6379
        assert redis_service.db == 0
        
    @pytest.mark.asyncio
    async def test_get_pool_connection_failure(self, redis_service):
        """Test Redis pool creation with connection failure."""
        # Mock Redis to raise connection error
        with patch('aioredis.from_url') as mock_redis:
            mock_redis.side_effect = ConnectionError("Connection failed")
            
            pool = await redis_service.get_pool()
            assert pool is None
            
    @pytest.mark.asyncio
    async def test_set_and_get_json(self, redis_service):
        """Test JSON set and get operations."""
        # Mock successful Redis operations
        with patch.object(redis_service, 'get_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_get_pool.return_value = mock_pool
            
            # Test set_json
            await redis_service.set_json("test_key", {"data": "test"}, ttl=300)
            mock_pool.setex.assert_called_once()
            
            # Test get_json
            mock_pool.get.return_value = '{"data": "test"}'
            result = await redis_service.get_json("test_key")
            assert result == {"data": "test"}
            
    @pytest.mark.asyncio
    async def test_rate_limit_check(self, redis_service):
        """Test rate limiting functionality."""
        with patch.object(redis_service, 'get_pool') as mock_get_pool:
            mock_pool = AsyncMock()
            mock_get_pool.return_value = mock_pool
            
            # Mock pipeline operations
            mock_pipe = AsyncMock()
            mock_pool.pipeline.return_value = mock_pipe
            mock_pipe.execute.return_value = [5, 300]  # 5 requests, 300 seconds TTL
            
            # Test rate limit check (under limit)
            is_allowed = await redis_service.check_rate_limit("test_client", 10, 60)
            assert is_allowed is True
            
            # Test rate limit check (over limit)
            mock_pipe.execute.return_value = [15, 300]  # 15 requests, over limit of 10
            is_allowed = await redis_service.check_rate_limit("test_client", 10, 60)
            assert is_allowed is False


class TestStreamingService:
    """Test streaming service functionality."""
    
    @pytest.fixture
    def streaming_service(self):
        """Create streaming service instance."""
        return StreamingService()
        
    def test_streaming_service_initialization(self, streaming_service):
        """Test streaming service initialization."""
        assert streaming_service.default_cache_ttl > 0
        assert "youtube" in streaming_service.platform_cache_ttls
        assert "bilibili" in streaming_service.platform_cache_ttls
        
    def test_get_cache_key(self, streaming_service):
        """Test cache key generation."""
        key = streaming_service._get_cache_key("youtube", "dQw4w9WgXcQ")
        assert key == "stream:youtube:dQw4w9WgXcQ"
        
    def test_get_platform_ttl(self, streaming_service):
        """Test platform-specific TTL retrieval."""
        # Test known platform
        ttl = streaming_service._get_platform_ttl("youtube")
        assert ttl == streaming_service.platform_cache_ttls["youtube"]
        
        # Test unknown platform
        ttl = streaming_service._get_platform_ttl("unknown")
        assert ttl == streaming_service.default_cache_ttl
        
    @pytest.mark.asyncio
    async def test_get_cached_stream_hit(self, streaming_service):
        """Test cache hit scenario."""
        cache_key = "stream:youtube:test"
        cached_data = {
            "stream_url": "https://example.com/stream",
            "video_info": {"title": "Test Video"},
            "timestamp": 1234567890
        }
        
        with patch.object(streaming_service, '_get_cache_key', return_value=cache_key):
            with patch('app.services.redis_service.redis_service.get_json', 
                      return_value=cached_data):
                result = await streaming_service._get_cached_stream("youtube", "test")
                assert result == cached_data
                
    @pytest.mark.asyncio
    async def test_get_cached_stream_miss(self, streaming_service):
        """Test cache miss scenario."""
        cache_key = "stream:youtube:test"
        
        with patch.object(streaming_service, '_get_cache_key', return_value=cache_key):
            with patch('app.services.redis_service.redis_service.get_json', 
                      return_value=None):
                result = await streaming_service._get_cached_stream("youtube", "test")
                assert result is None
                
    @pytest.mark.asyncio
    async def test_validate_stream_url_success(self, streaming_service):
        """Test successful URL validation."""
        test_url = "https://example.com/stream"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            result = await streaming_service.validate_stream_url(test_url)
            assert result is True
            
    @pytest.mark.asyncio
    async def test_validate_stream_url_failure(self, streaming_service):
        """Test URL validation failure."""
        test_url = "https://example.com/stream"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            result = await streaming_service.validate_stream_url(test_url)
            assert result is False
            
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, streaming_service):
        """Test cache statistics retrieval."""
        mock_keys = ["stream:youtube:video1", "stream:bilibili:video2", "stream:youtube:video3"]
        
        with patch('app.services.redis_service.redis_service.get_keys', 
                  return_value=mock_keys):
            stats = await streaming_service.get_cache_stats()
            
            assert stats["total_cached_streams"] == 3
            assert stats["platform_breakdown"]["youtube"] == 2
            assert stats["platform_breakdown"]["bilibili"] == 1
            assert "timestamp" in stats


class TestServiceIntegration:
    """Test service integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_streaming_service_with_redis_unavailable(self):
        """Test streaming service behavior when Redis is unavailable."""
        streaming_service = StreamingService()
        
        # Mock Redis to be unavailable
        with patch('app.services.redis_service.redis_service.get_json', 
                  side_effect=Exception("Redis unavailable")):
            # Should not raise exception, should return None
            result = await streaming_service._get_cached_stream("youtube", "test")
            assert result is None
            
    @pytest.mark.asyncio
    async def test_cache_operations_with_network_error(self):
        """Test cache operations with network errors."""
        streaming_service = StreamingService()
        
        with patch('app.services.redis_service.redis_service.set_json', 
                  side_effect=ConnectionError("Network error")):
            # Should not raise exception, should handle gracefully
            await streaming_service._cache_stream_data(
                "youtube", "test", "https://example.com", {"title": "Test"}
            )
            # If we get here without exception, the test passes
