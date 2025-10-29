"""Redis service for caching and rate limiting."""

import asyncio
import json
import time
from typing import Optional, Dict, Any
import redis.asyncio as redis
from app.config import settings
from app.exceptions import ServiceUnavailableError
import logging

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching and data persistence."""
    
    def __init__(self):
        self._pool: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()
    
    async def get_pool(self) -> redis.Redis:
        """Get Redis connection pool with lazy initialization."""
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    try:
                        self._pool = redis.from_url(
                            settings.get_redis_url(),
                            encoding="utf-8",
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5,
                            retry_on_timeout=True,
                            health_check_interval=30
                        )
                        # Test connection
                        await self._pool.ping()
                        logger.info("Redis connection established")
                    except Exception as e:
                        logger.debug(f"Redis unavailable: {e}")
                        raise ServiceUnavailableError(
                            "Redis service unavailable",
                            code="REDIS_CONNECTION_ERROR",
                            detail=str(e)
                        )
        return self._pool
    
    async def close(self):
        """Close Redis connection."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store JSON data in Redis."""
        try:
            pool = await self.get_pool()
            serialized = json.dumps(value)
            if ttl:
                return await pool.setex(key, ttl, serialized)
            else:
                return await pool.set(key, serialized)
        except Exception as e:
            logger.debug(f"Redis unavailable for set: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve JSON data from Redis."""
        try:
            pool = await self.get_pool()
            data = await pool.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug(f"Redis unavailable for get: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            pool = await self.get_pool()
            return bool(await pool.delete(key))
        except Exception as e:
            logger.error(f"Error deleting key from Redis: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            pool = await self.get_pool()
            return bool(await pool.exists(key))
        except Exception as e:
            logger.error(f"Error checking key existence in Redis: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment counter in Redis."""
        try:
            pool = await self.get_pool()
            async with pool.pipeline() as pipe:
                await pipe.incr(key, amount)
                if ttl:
                    await pipe.expire(key, ttl)
                results = await pipe.execute()
                return results[0]
        except Exception as e:
            logger.error(f"Error incrementing counter in Redis: {e}")
            return 0
    
    async def check_rate_limit(self, client_id: str, window: int, max_requests: int) -> tuple[bool, int]:
        """
        Check rate limit using sliding window algorithm.
        Returns (is_allowed, requests_count).
        """
        try:
            pool = await self.get_pool()
            key = f"rate_limit:{client_id}"
            now = int(time.time())
            
            async with pool.pipeline() as pipe:
                # Remove old entries
                await pipe.zremrangebyscore(key, 0, now - window)
                # Add current request
                await pipe.zadd(key, {now: now})
                # Count requests in window
                await pipe.zcard(key)
                # Set expiration
                await pipe.expire(key, window)
                
                results = await pipe.execute()
                request_count = results[2]
                
                is_allowed = request_count <= max_requests
                return is_allowed, request_count
                
        except Exception as e:
            logger.debug(f"Redis unavailable for rate limiting: {e}")
            # Fail open - allow request if Redis is down
            return True, 0
    
    async def get_health(self) -> Dict[str, Any]:
        """Get Redis health status."""
        try:
            pool = await self.get_pool()
            info = await pool.info()
            await pool.ping()
            
            return {
                "status": "healthy",
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "uptime_in_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global Redis service instance
redis_service = RedisService()
