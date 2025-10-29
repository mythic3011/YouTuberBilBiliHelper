"""
Robust Streaming Service with Enhanced Error Handling

Addresses ContentLengthError and other streaming issues that occur with
concurrent access and unreliable upstream servers.
"""

import asyncio
import aiohttp
import time
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from pathlib import Path

from app.services.streaming.proxy_service import StreamingService
from app.services.infrastructure.redis_service import redis_service
from app.exceptions import ServiceUnavailableError, VideoNotFoundError
from app.config import settings

logger = logging.getLogger(__name__)


class RobustStreamingService(StreamingService):
    """Enhanced streaming service with robust error handling for concurrent access."""
    
    def __init__(self):
        super().__init__()
        self._active_streams: Dict[str, int] = {}  # Track active streams per video
        self._stream_semaphores: Dict[str, asyncio.Semaphore] = {}  # Per-video concurrency limits
        self._retry_delays = [1, 2, 4]  # Progressive retry delays
        
    async def get_robust_stream_semaphore(self, stream_key: str, max_concurrent: int = 3) -> asyncio.Semaphore:
        """Get or create a semaphore for limiting concurrent streams per video."""
        if stream_key not in self._stream_semaphores:
            self._stream_semaphores[stream_key] = asyncio.Semaphore(max_concurrent)
        return self._stream_semaphores[stream_key]
    
    async def proxy_video_stream_robust(
        self,
        platform: str,
        video_id: str,
        quality: str = "best",
        max_retries: int = 3,
        chunk_size: int = 8192,
        timeout: int = 300
    ) -> AsyncGenerator[bytes, None]:
        """
        Robust video stream proxy with enhanced error handling.
        
        Addresses:
        - ContentLengthError: Not enough data to satisfy content length header
        - Connection timeouts and resets
        - Concurrent access issues
        - Upstream server instability
        """
        
        stream_key = f"{platform}:{video_id}:{quality}"
        
        # Limit concurrent streams for the same video to prevent overload
        semaphore = await self.get_robust_stream_semaphore(stream_key, max_concurrent=2)
        
        async with semaphore:
            # Track active stream
            self._active_streams[stream_key] = self._active_streams.get(stream_key, 0) + 1
            
            try:
                async for chunk in self._stream_with_retry(
                    platform, video_id, quality, max_retries, chunk_size, timeout
                ):
                    yield chunk
                    
            finally:
                # Clean up active stream tracking
                self._active_streams[stream_key] = max(0, self._active_streams.get(stream_key, 1) - 1)
                if self._active_streams[stream_key] == 0:
                    self._active_streams.pop(stream_key, None)
    
    async def _stream_with_retry(
        self,
        platform: str,
        video_id: str,
        quality: str,
        max_retries: int,
        chunk_size: int,
        timeout: int
    ) -> AsyncGenerator[bytes, None]:
        """Stream with retry logic for handling various error conditions."""
        
        for attempt in range(max_retries + 1):
            try:
                async for chunk in self._execute_stream(platform, video_id, quality, chunk_size, timeout):
                    yield chunk
                
                # If we get here, streaming was successful
                return
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Analyze error type and decide if retry is appropriate
                should_retry, delay = self._analyze_streaming_error(error_msg, attempt, max_retries)
                
                if should_retry and attempt < max_retries:
                    logger.warning(
                        f"Streaming attempt {attempt + 1} failed for {platform}/{video_id}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed or error is not retryable
                    logger.error(f"Streaming failed after {attempt + 1} attempts for {platform}/{video_id}: {e}")
                    raise ServiceUnavailableError(f"Stream failed: {self._format_streaming_error(error_msg)}")
    
    def _analyze_streaming_error(self, error_msg: str, attempt: int, max_retries: int) -> tuple[bool, float]:
        """
        Analyze streaming error to determine if retry is appropriate and calculate delay.
        
        Returns: (should_retry, delay_seconds)
        """
        
        # Retryable errors
        retryable_patterns = [
            "content length",           # ContentLengthError
            "connection reset",         # Connection issues
            "connection timeout",       # Timeout issues
            "server disconnected",      # Server issues
            "incomplete read",          # Incomplete data
            "connection closed",        # Premature connection close
            "bad gateway",             # 502 errors
            "service unavailable",     # 503 errors
            "gateway timeout",         # 504 errors
        ]
        
        # Non-retryable errors
        non_retryable_patterns = [
            "not found",              # 404 errors
            "forbidden",              # 403 errors
            "unauthorized",           # 401 errors
            "bad request",            # 400 errors (except ContentLength)
            "unsupported",            # Format issues
        ]
        
        # Check for non-retryable errors first
        for pattern in non_retryable_patterns:
            if pattern in error_msg:
                return False, 0.0
        
        # Check for retryable errors
        for pattern in retryable_patterns:
            if pattern in error_msg:
                # Use progressive delay
                delay = self._retry_delays[min(attempt, len(self._retry_delays) - 1)]
                return True, delay
        
        # Unknown error - retry with caution
        if attempt < max_retries:
            return True, 2.0  # Default delay
        
        return False, 0.0
    
    def _format_streaming_error(self, error_msg: str) -> str:
        """Format streaming error for user-friendly response."""
        
        if "content length" in error_msg:
            return (
                "Stream interrupted due to content length mismatch. "
                "This often occurs with concurrent access or unstable upstream servers. "
                "Please try again or use a different quality setting."
            )
        elif "connection" in error_msg:
            return (
                "Network connection issue occurred during streaming. "
                "This may be due to network instability or server overload. "
                "Please try again in a moment."
            )
        elif "timeout" in error_msg:
            return (
                "Stream request timed out. "
                "The server may be overloaded or the video is very large. "
                "Try a lower quality or retry later."
            )
        else:
            return f"Streaming error: {error_msg}"
    
    async def _execute_stream(
        self,
        platform: str,
        video_id: str,
        quality: str,
        chunk_size: int,
        timeout: int
    ) -> AsyncGenerator[bytes, None]:
        """Execute the actual streaming with enhanced error handling."""
        
        # Get stream URL
        stream_data = await self.get_stream_url(platform, video_id, quality)
        stream_url = stream_data["stream_url"]
        
        # Enhanced timeout configuration
        timeout_config = aiohttp.ClientTimeout(
            total=timeout,
            connect=30,      # Connection timeout
            sock_read=60,    # Socket read timeout
            sock_connect=10  # Socket connection timeout
        )
        
        # Enhanced session configuration
        connector = aiohttp.TCPConnector(
            limit=100,              # Total connection limit
            limit_per_host=10,      # Per-host connection limit
            ttl_dns_cache=300,      # DNS cache TTL
            use_dns_cache=True,     # Enable DNS caching
            keepalive_timeout=60,   # Keep-alive timeout
            enable_cleanup_closed=True  # Clean up closed connections
        )
        
        session_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',  # Disable compression to avoid content-length issues
            'Connection': 'keep-alive',
            'Range': 'bytes=0-',  # Request range support
        }
        
        # Add platform-specific headers
        platform_headers = await self.get_streaming_headers(platform)
        session_headers.update(platform_headers)
        
        async with aiohttp.ClientSession(
            timeout=timeout_config,
            connector=connector,
            headers=session_headers
        ) as session:
            
            try:
                async with session.get(stream_url, allow_redirects=True) as response:
                    # Check response status
                    if response.status not in [200, 206]:  # 206 for partial content
                        raise ServiceUnavailableError(f"Stream unavailable: HTTP {response.status}")
                    
                    # Log response headers for debugging
                    content_length = response.headers.get('Content-Length')
                    content_type = response.headers.get('Content-Type', 'unknown')
                    accept_ranges = response.headers.get('Accept-Ranges', 'none')
                    
                    logger.debug(
                        f"Streaming {platform}/{video_id}: "
                        f"Content-Length={content_length}, "
                        f"Content-Type={content_type}, "
                        f"Accept-Ranges={accept_ranges}"
                    )
                    
                    # Stream chunks with enhanced error handling
                    bytes_streamed = 0
                    
                    try:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            if chunk:
                                bytes_streamed += len(chunk)
                                yield chunk
                            
                    except Exception as e:
                        # Log streaming statistics for debugging
                        logger.error(
                            f"Streaming interrupted for {platform}/{video_id} "
                            f"after {bytes_streamed} bytes: {e}"
                        )
                        
                        # Re-raise with context
                        if "content length" in str(e).lower():
                            raise Exception(f"ContentLengthError: Streamed {bytes_streamed} bytes, expected {content_length}")
                        else:
                            raise
                    
                    # Log successful streaming
                    logger.info(f"Successfully streamed {bytes_streamed} bytes for {platform}/{video_id}")
                    
            except aiohttp.ClientError as e:
                # Enhanced aiohttp error handling
                error_type = type(e).__name__
                logger.error(f"aiohttp error ({error_type}) for {platform}/{video_id}: {e}")
                
                # Map specific aiohttp errors to user-friendly messages
                if "ContentLengthError" in error_type:
                    raise Exception("Content length mismatch - incomplete stream data")
                elif "ClientTimeout" in error_type:
                    raise Exception("Connection timeout - server response too slow")
                elif "ClientConnectorError" in error_type:
                    raise Exception("Connection failed - unable to reach server")
                elif "ServerDisconnectedError" in error_type:
                    raise Exception("Server disconnected - connection closed prematurely")
                else:
                    raise Exception(f"Network error: {str(e)}")
    
    async def get_stream_health_info(self, platform: str, video_id: str) -> Dict[str, Any]:
        """Get health information about a stream."""
        
        stream_key = f"{platform}:{video_id}"
        active_streams = self._active_streams.get(stream_key, 0)
        
        # Test stream availability
        try:
            stream_data = await self.get_stream_url(platform, video_id, "worst")  # Use lowest quality for test
            stream_available = True
            stream_url = stream_data["stream_url"]
        except Exception as e:
            stream_available = False
            stream_url = None
        
        return {
            "platform": platform,
            "video_id": video_id,
            "stream_available": stream_available,
            "active_concurrent_streams": active_streams,
            "stream_url_available": stream_url is not None,
            "concurrent_limit": 2,  # Our configured limit
            "health_status": "healthy" if stream_available and active_streams < 2 else "degraded"
        }
    
    async def get_streaming_statistics(self) -> Dict[str, Any]:
        """Get comprehensive streaming statistics."""
        
        total_active_streams = sum(self._active_streams.values())
        unique_videos_streaming = len(self._active_streams)
        
        # Calculate stream distribution
        stream_distribution = {}
        for stream_key, count in self._active_streams.items():
            platform = stream_key.split(':')[0]
            stream_distribution[platform] = stream_distribution.get(platform, 0) + count
        
        return {
            "streaming_statistics": {
                "total_active_streams": total_active_streams,
                "unique_videos_streaming": unique_videos_streaming,
                "stream_distribution": stream_distribution,
                "concurrent_limits": {
                    "per_video": 2,
                    "total_system": 100
                }
            },
            "error_handling": {
                "retry_enabled": True,
                "max_retries": 3,
                "retry_delays": self._retry_delays,
                "content_length_error_handling": "enhanced",
                "timeout_handling": "progressive",
                "connection_pooling": "enabled"
            },
            "performance_optimizations": {
                "dns_caching": True,
                "connection_reuse": True,
                "compression_disabled": True,  # Prevents content-length issues
                "range_requests": True,
                "cleanup_enabled": True
            }
        }
    
    async def test_stream_reliability(self, platform: str, video_id: str, test_duration: int = 10) -> Dict[str, Any]:
        """Test stream reliability for a specific video."""
        
        test_results = {
            "platform": platform,
            "video_id": video_id,
            "test_duration_seconds": test_duration,
            "start_time": time.time(),
            "success": False,
            "bytes_streamed": 0,
            "chunks_received": 0,
            "errors_encountered": [],
            "performance_metrics": {}
        }
        
        try:
            start_time = time.time()
            bytes_count = 0
            chunk_count = 0
            
            # Test streaming for specified duration
            async for chunk in self.proxy_video_stream_robust(platform, video_id, "worst"):
                bytes_count += len(chunk)
                chunk_count += 1
                
                # Stop test after duration
                if time.time() - start_time > test_duration:
                    break
            
            end_time = time.time()
            duration = end_time - start_time
            
            test_results.update({
                "success": True,
                "bytes_streamed": bytes_count,
                "chunks_received": chunk_count,
                "actual_duration": duration,
                "performance_metrics": {
                    "bytes_per_second": bytes_count / duration if duration > 0 else 0,
                    "chunks_per_second": chunk_count / duration if duration > 0 else 0,
                    "average_chunk_size": bytes_count / chunk_count if chunk_count > 0 else 0
                }
            })
            
        except Exception as e:
            test_results["errors_encountered"].append({
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": time.time()
            })
        
        test_results["end_time"] = time.time()
        return test_results


# Global instance
robust_streaming_service = RobustStreamingService()
