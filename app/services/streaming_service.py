"""Enhanced streaming service focused on proxy functionality."""

import asyncio
import time
import hashlib
from typing import Optional, Dict, Any, AsyncGenerator
from urllib.parse import urlparse
import aiohttp
from app.config import settings
from app.services.redis_service import redis_service
from app.services.video_service import video_service
from app.exceptions import VideoNotFoundError, ServiceUnavailableError
import logging

logger = logging.getLogger(__name__)


class StreamingService:
    """Core streaming proxy service with intelligent caching."""
    
    def __init__(self):
        from app.config import settings
        self.settings = settings
        self.default_cache_ttl = settings.stream_cache_ttl
        self.platform_cache_ttls = {
            "youtube": settings.youtube_cache_ttl,
            "bilibili": settings.bilibili_cache_ttl,
            "twitch": settings.twitch_cache_ttl,
            "instagram": settings.instagram_cache_ttl,
            "twitter": settings.twitter_cache_ttl
        }
    
    async def get_stream_url(
        self, 
        platform: str, 
        video_id: str, 
        quality: str = "best",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get direct stream URL with intelligent caching."""
        
        cache_key = self._generate_cache_key(platform, video_id, quality)
        
        # Try cache first
        if use_cache:
            cached_result = await self._get_cached_stream(cache_key)
            if cached_result:
                logger.info(f"Cache hit for {platform}:{video_id}")
                return cached_result
        
        # Extract fresh stream URL
        try:
            stream_data = await self._extract_fresh_stream(platform, video_id, quality)
            
            # Cache the result
            if use_cache:
                await self._cache_stream_data(cache_key, stream_data, platform)
            
            logger.info(f"Fresh extraction for {platform}:{video_id}")
            return stream_data
            
        except Exception as e:
            logger.error(f"Failed to extract stream for {platform}:{video_id}: {e}")
            raise VideoNotFoundError(f"Could not extract stream: {str(e)}")
    
    async def proxy_video_stream(
        self, 
        platform: str, 
        video_id: str, 
        quality: str = "best"
    ) -> AsyncGenerator[bytes, None]:
        """Proxy video stream through our server."""
        
        # Get stream URL
        stream_data = await self.get_stream_url(platform, video_id, quality)
        stream_url = stream_data["stream_url"]
        
        # Stream the content
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
            try:
                async with session.get(stream_url) as response:
                    if response.status != 200:
                        raise ServiceUnavailableError(f"Stream unavailable: HTTP {response.status}")
                    
                    # Stream chunks
                    async for chunk in response.content.iter_chunked(8192):
                        yield chunk
                        
            except aiohttp.ClientError as e:
                logger.error(f"Proxy streaming error: {e}")
                raise ServiceUnavailableError(f"Streaming failed: {str(e)}")
    
    async def get_adaptive_stream_url(
        self, 
        platform: str, 
        video_id: str,
        bandwidth_kbps: Optional[int] = None,
        device_type: str = "desktop"
    ) -> Dict[str, Any]:
        """Get adaptively selected stream URL based on client capabilities."""
        
        # Get video info to understand available qualities
        try:
            video_info = await video_service.get_video_info(f"https://example.com/{video_id}")
            
            # Simple adaptive logic based on bandwidth and device
            selected_quality = self._select_adaptive_quality(
                video_info.formats if hasattr(video_info, 'formats') else [],
                bandwidth_kbps,
                device_type
            )
            
            return await self.get_stream_url(platform, video_id, selected_quality)
            
        except Exception as e:
            logger.warning(f"Adaptive selection failed, falling back to default: {e}")
            return await self.get_stream_url(platform, video_id, "best")
    
    async def batch_stream_urls(
        self, 
        requests: list[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Get multiple stream URLs efficiently."""
        
        results = {}
        tasks = []
        
        # Create tasks for concurrent processing
        for req in requests:
            platform = req.get("platform")
            video_id = req.get("video_id")
            quality = req.get("quality", "best")
            
            if platform and video_id:
                task = asyncio.create_task(
                    self._safe_get_stream_url(platform, video_id, quality)
                )
                tasks.append((f"{platform}:{video_id}", task))
        
        # Wait for all tasks to complete
        for key, task in tasks:
            try:
                result = await task
                results[key] = {"success": True, "data": result}
            except Exception as e:
                results[key] = {"success": False, "error": str(e)}
        
        return {
            "results": results,
            "total": len(requests),
            "successful": sum(1 for r in results.values() if r["success"]),
            "failed": sum(1 for r in results.values() if not r["success"])
        }
    
    def _generate_cache_key(self, platform: str, video_id: str, quality: str) -> str:
        """Generate consistent cache key."""
        key_string = f"stream:{platform}:{video_id}:{quality}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _get_cached_stream(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached stream data."""
        try:
            cached_data = await redis_service.get_json(cache_key)
            if cached_data:
                # Check if URL is still valid (simple TTL check)
                expires_at = cached_data.get("expires_at", 0)
                if time.time() < expires_at:
                    return cached_data
                else:
                    # Clean up expired cache
                    await redis_service.delete(cache_key)
            return None
        except Exception as e:
            logger.debug(f"Cache unavailable, continuing without cache: {e}")
            return None
    
    async def _cache_stream_data(
        self, 
        cache_key: str, 
        stream_data: Dict[str, Any], 
        platform: str
    ):
        """Cache stream data with appropriate TTL."""
        try:
            # Add expiration timestamp
            ttl = self.platform_cache_ttls.get(platform, self.default_cache_ttl)
            stream_data["expires_at"] = time.time() + ttl
            stream_data["cached_at"] = time.time()
            
            await redis_service.set_json(cache_key, stream_data, ttl=ttl)
        except Exception as e:
            logger.debug(f"Cache unavailable, continuing without cache: {e}")
    
    async def _extract_fresh_stream(
        self, 
        platform: str, 
        video_id: str, 
        quality: str
    ) -> Dict[str, Any]:
        """Extract fresh stream URL from platform."""
        
        # Build full URL for the video service
        platform_urls = {
            "youtube": f"https://www.youtube.com/watch?v={video_id}",
            "bilibili": f"https://www.bilibili.com/video/{video_id}",
            "instagram": f"https://www.instagram.com/p/{video_id}/",
            "twitter": f"https://twitter.com/user/status/{video_id}",
            "twitch": f"https://www.twitch.tv/videos/{video_id}"
        }
        
        if platform not in platform_urls:
            raise VideoNotFoundError(f"Unsupported platform: {platform}")
        
        url = platform_urls[platform]
        
        # Get video info and stream URL
        video_info = await video_service.get_video_info(url)
        stream_url = await video_service.get_stream_url(url, quality)
        
        return {
            "stream_url": stream_url,
            "quality": quality,
            "platform": platform,
            "video_id": video_id,
            "video_info": {
                "title": video_info.title,
                "duration": video_info.duration,
                "thumbnail": video_info.thumbnail,
                "uploader": video_info.uploader
            },
            "extracted_at": time.time()
        }
    
    def _select_adaptive_quality(
        self, 
        available_formats: list, 
        bandwidth_kbps: Optional[int],
        device_type: str
    ) -> str:
        """Select optimal quality based on client capabilities."""
        
        # Simple adaptive logic
        if device_type == "mobile":
            if bandwidth_kbps and bandwidth_kbps < 1000:  # < 1 Mbps
                return "480p"
            elif bandwidth_kbps and bandwidth_kbps < 3000:  # < 3 Mbps
                return "720p"
            else:
                return "720p"  # Cap mobile at 720p
        else:  # desktop
            if bandwidth_kbps and bandwidth_kbps < 2000:  # < 2 Mbps
                return "720p"
            elif bandwidth_kbps and bandwidth_kbps < 5000:  # < 5 Mbps
                return "1080p"
            else:
                return "best"
    
    async def _safe_get_stream_url(
        self, 
        platform: str, 
        video_id: str, 
        quality: str
    ) -> Dict[str, Any]:
        """Safely get stream URL with error handling."""
        try:
            return await self.get_stream_url(platform, video_id, quality)
        except Exception as e:
            logger.error(f"Failed to get stream URL for {platform}:{video_id}: {e}")
            raise
    
    async def get_streaming_headers(
        self, 
        platform: str,
        content_type: str = "video/mp4"
    ) -> Dict[str, str]:
        """Get appropriate headers for streaming response."""
        
        headers = {
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD",
            "X-Platform": platform,
            "X-Served-By": "YouTuberBilBiliHelper"
        }
        
        # Platform-specific headers
        if platform == "youtube":
            headers["Cache-Control"] = "public, max-age=1800"  # Shorter cache for YouTube
        elif platform == "tiktok":
            headers["Cache-Control"] = "public, max-age=900"   # Very short cache for TikTok
        
        return headers
    
    async def validate_stream_url(self, url: str) -> bool:
        """Validate if stream URL is still accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics."""
        try:
            # Simple cache statistics
            pool = await redis_service.get_pool()
            cache_keys = await pool.keys("stream:*")
            
            platform_counts = {}
            total_cached = len(cache_keys) if cache_keys else 0
            
            # Count by platform (simplified)
            for key in cache_keys or []:
                try:
                    platform = key.split(":")[1] if ":" in key else "unknown"
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error parsing cache key '{key}': {e}")
                    continue
            
            return {
                "total_cached_streams": total_cached,
                "platform_breakdown": platform_counts,
                "cache_hit_rate": "N/A",  # Would need tracking to implement
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Global streaming service instance
streaming_service = StreamingService()
