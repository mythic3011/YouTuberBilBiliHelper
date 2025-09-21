#!/usr/bin/env python3
"""
FastAPI Performance Optimization Examples
Demonstrates how to optimize your current FastAPI application for better performance.
"""

import asyncio
import time
import uvloop
from typing import AsyncGenerator
import aiohttp
import orjson
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import redis.asyncio as redis
from contextlib import asynccontextmanager


# 1. Use uvloop for better async performance
def setup_uvloop():
    """Setup uvloop for better async performance (Linux/macOS only)"""
    try:
        uvloop.install()
        print("✅ uvloop installed - async performance improved")
    except ImportError:
        print("⚠️ uvloop not available - using default event loop")


# 2. Optimized HTTP client with connection pooling
class OptimizedHTTPClient:
    """Optimized HTTP client with connection pooling and timeouts"""
    
    def __init__(self):
        # Configure connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=60,
            enable_cleanup_closed=True
        )
        
        # Configure timeouts
        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout
            connect=5,  # Connection timeout
            sock_read=10  # Socket read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'OptimizedVideoProxy/2.0'
            }
        )
    
    async def close(self):
        """Close the HTTP session"""
        await self.session.close()
    
    async def stream_content(self, url: str, chunk_size: int = 8192) -> AsyncGenerator[bytes, None]:
        """Stream content from URL with optimized chunking"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        yield chunk
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            raise


# 3. Optimized Redis connection with connection pooling
class OptimizedRedisClient:
    """Optimized Redis client with connection pooling"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.pool = None
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        self.pool = redis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30
        )
        self.client = redis.Redis(connection_pool=self.pool)
        print("✅ Redis connection pool initialized")
    
    async def close(self):
        """Close Redis connection pool"""
        if self.pool:
            await self.pool.disconnect()
    
    async def get_cached(self, key: str):
        """Get cached data with optimized JSON parsing"""
        try:
            data = await self.client.get(key)
            if data:
                return orjson.loads(data)
            return None
        except Exception as e:
            print(f"❌ Redis get error: {e}")
            return None
    
    async def set_cached(self, key: str, value: dict, ttl: int = 3600):
        """Set cached data with optimized JSON serialization"""
        try:
            serialized = orjson.dumps(value)
            await self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"❌ Redis set error: {e}")
            return False


# 4. Global instances
http_client = OptimizedHTTPClient()
redis_client = OptimizedRedisClient()


# 5. Optimized FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with proper resource management"""
    # Startup
    print("🚀 Starting optimized FastAPI application...")
    setup_uvloop()
    await redis_client.initialize()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down optimized FastAPI application...")
    await http_client.close()
    await redis_client.close()


app = FastAPI(
    title="Optimized Video Streaming API",
    description="High-performance video streaming API with optimizations",
    version="2.0.0",
    lifespan=lifespan
)


# 6. Optimized streaming endpoint
@app.get("/stream/optimized/{platform}/{video_id}")
async def optimized_stream_video(platform: str, video_id: str):
    """Optimized video streaming endpoint with caching and performance improvements"""
    
    cache_key = f"stream:{platform}:{video_id}"
    
    # Check cache first
    cached_url = await redis_client.get_cached(cache_key)
    if cached_url:
        stream_url = cached_url.get("url")
        print(f"✅ Cache hit for {cache_key}")
    else:
        # Simulate video URL extraction (replace with actual yt-dlp logic)
        stream_url = f"https://example.com/video/{video_id}.mp4"
        
        # Cache the result
        await redis_client.set_cached(cache_key, {"url": stream_url}, ttl=1800)
        print(f"📦 Cached {cache_key}")
    
    # Stream the video with optimized chunking
    async def generate_stream():
        start_time = time.time()
        bytes_streamed = 0
        
        try:
            async for chunk in http_client.stream_content(stream_url, chunk_size=16384):
                bytes_streamed += len(chunk)
                yield chunk
        except Exception as e:
            print(f"❌ Streaming failed: {e}")
            yield b""  # End stream gracefully
        finally:
            duration = time.time() - start_time
            print(f"📊 Streamed {bytes_streamed:,} bytes in {duration:.2f}s")
    
    return StreamingResponse(
        generate_stream(),
        media_type="video/mp4",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes"
        }
    )


# 7. Performance monitoring endpoint
@app.get("/performance/stats")
async def get_performance_stats():
    """Get performance statistics"""
    
    # Get Redis info
    redis_info = {}
    try:
        info = await redis_client.client.info()
        redis_info = {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0)
        }
    except Exception as e:
        redis_info = {"error": str(e)}
    
    # Get HTTP client stats
    http_stats = {
        "connector_limit": 100,
        "connector_limit_per_host": 30,
        "session_closed": http_client.session.closed
    }
    
    return Response(
        content=orjson.dumps({
            "timestamp": time.time(),
            "redis": redis_info,
            "http_client": http_stats,
            "event_loop": {
                "type": "uvloop" if "uvloop" in str(type(asyncio.get_event_loop())) else "asyncio",
                "running": asyncio.get_event_loop().is_running()
            }
        }),
        media_type="application/json"
    )


# 8. Batch processing endpoint for multiple videos
@app.post("/batch/process")
async def batch_process_videos(video_requests: list[dict]):
    """Process multiple video requests concurrently"""
    
    async def process_single_video(request: dict):
        """Process a single video request"""
        platform = request.get("platform")
        video_id = request.get("video_id")
        
        cache_key = f"batch:{platform}:{video_id}"
        
        # Simulate processing with cache check
        cached_result = await redis_client.get_cached(cache_key)
        if cached_result:
            return {"video_id": video_id, "status": "cached", "data": cached_result}
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        result = {
            "url": f"https://example.com/{platform}/{video_id}.mp4",
            "title": f"Video {video_id}",
            "duration": 120
        }
        
        # Cache the result
        await redis_client.set_cached(cache_key, result, ttl=3600)
        
        return {"video_id": video_id, "status": "processed", "data": result}
    
    # Process all requests concurrently
    start_time = time.time()
    
    # Limit concurrent processing to prevent overload
    semaphore = asyncio.Semaphore(10)
    
    async def process_with_semaphore(request):
        async with semaphore:
            return await process_single_video(request)
    
    results = await asyncio.gather(
        *[process_with_semaphore(req) for req in video_requests],
        return_exceptions=True
    )
    
    processing_time = time.time() - start_time
    
    return Response(
        content=orjson.dumps({
            "total_requests": len(video_requests),
            "processing_time": round(processing_time, 3),
            "requests_per_second": round(len(video_requests) / processing_time, 2),
            "results": results
        }),
        media_type="application/json"
    )


# 9. Health check with performance metrics
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with performance metrics"""
    
    start_time = time.time()
    
    # Test Redis connection
    redis_healthy = False
    redis_latency = None
    try:
        redis_start = time.time()
        await redis_client.client.ping()
        redis_latency = (time.time() - redis_start) * 1000
        redis_healthy = True
    except Exception as e:
        redis_latency = f"Error: {e}"
    
    # Test HTTP client
    http_healthy = False
    http_latency = None
    try:
        http_start = time.time()
        async with http_client.session.get("https://httpbin.org/status/200") as response:
            if response.status == 200:
                http_latency = (time.time() - http_start) * 1000
                http_healthy = True
    except Exception as e:
        http_latency = f"Error: {e}"
    
    total_latency = (time.time() - start_time) * 1000
    
    health_data = {
        "status": "healthy" if redis_healthy and http_healthy else "unhealthy",
        "timestamp": time.time(),
        "checks": {
            "redis": {
                "healthy": redis_healthy,
                "latency_ms": redis_latency
            },
            "http_client": {
                "healthy": http_healthy,
                "latency_ms": http_latency
            }
        },
        "total_check_time_ms": round(total_latency, 2),
        "optimizations": {
            "uvloop_enabled": "uvloop" in str(type(asyncio.get_event_loop())),
            "connection_pooling": True,
            "json_optimization": True,
            "async_optimized": True
        }
    }
    
    return Response(
        content=orjson.dumps(health_data),
        media_type="application/json"
    )


# 10. Performance testing utilities
class PerformanceTester:
    """Utility class for performance testing"""
    
    @staticmethod
    async def benchmark_endpoint(url: str, concurrent_requests: int = 10, total_requests: int = 100):
        """Benchmark an endpoint with concurrent requests"""
        
        async def make_request(session: aiohttp.ClientSession):
            start_time = time.time()
            try:
                async with session.get(url) as response:
                    await response.read()
                    return {
                        "status": response.status,
                        "latency": (time.time() - start_time) * 1000,
                        "success": True
                    }
            except Exception as e:
                return {
                    "status": 0,
                    "latency": (time.time() - start_time) * 1000,
                    "success": False,
                    "error": str(e)
                }
        
        # Create HTTP session for testing
        connector = aiohttp.TCPConnector(limit=concurrent_requests * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Run benchmark
            start_time = time.time()
            
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def request_with_semaphore():
                async with semaphore:
                    return await make_request(session)
            
            results = await asyncio.gather(
                *[request_with_semaphore() for _ in range(total_requests)],
                return_exceptions=True
            )
            
            total_time = time.time() - start_time
            
            # Calculate statistics
            successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_requests = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
            
            latencies = [r["latency"] for r in successful_requests]
            
            return {
                "total_requests": total_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "total_time": round(total_time, 3),
                "requests_per_second": round(total_requests / total_time, 2),
                "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
                "min_latency_ms": round(min(latencies), 2) if latencies else 0,
                "max_latency_ms": round(max(latencies), 2) if latencies else 0,
                "success_rate": round((len(successful_requests) / total_requests) * 100, 2)
            }


@app.post("/performance/benchmark")
async def run_performance_benchmark(config: dict):
    """Run performance benchmark on specified endpoint"""
    
    url = config.get("url", "http://localhost:8000/health/detailed")
    concurrent_requests = config.get("concurrent_requests", 10)
    total_requests = config.get("total_requests", 100)
    
    benchmark_results = await PerformanceTester.benchmark_endpoint(
        url, concurrent_requests, total_requests
    )
    
    return Response(
        content=orjson.dumps(benchmark_results),
        media_type="application/json"
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Optimized FastAPI Server")
    print("📊 Performance optimizations enabled:")
    print("   ✅ uvloop event loop")
    print("   ✅ Connection pooling")
    print("   ✅ Optimized JSON serialization (orjson)")
    print("   ✅ Redis connection pooling")
    print("   ✅ Async streaming")
    print("   ✅ Proper resource management")
    
    uvicorn.run(
        "fastapi_performance_optimizations:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Disable reload in production
        workers=1,  # Use multiple workers in production
        loop="uvloop",  # Use uvloop
        http="httptools",  # Use httptools for better HTTP parsing
        access_log=False,  # Disable access log for better performance
        log_level="info"
    )
