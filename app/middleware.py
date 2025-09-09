"""Middleware for the API."""

import time
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from app.config import settings
from app.services.redis_service import redis_service
from app.exceptions import RateLimitExceededError
import logging

logger = logging.getLogger(__name__)


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Rate limiting middleware."""
    if not settings.enable_rate_limiting:
        return await call_next(request)
    
    try:
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Check rate limit
        is_allowed, request_count = await redis_service.check_rate_limit(
            client_id,
            settings.rate_limit_window,
            settings.rate_limit_max_requests
        )
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {client_id}: {request_count} requests "
                f"in {settings.rate_limit_window}s window"
            )
            raise RateLimitExceededError(
                f"Rate limit exceeded. Maximum {settings.rate_limit_max_requests} "
                f"requests per {settings.rate_limit_window} seconds allowed.",
                code="RATE_LIMIT_EXCEEDED"
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, settings.rate_limit_max_requests - request_count)
        )
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + settings.rate_limit_window)
        
        return response
        
    except RateLimitExceededError:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Maximum {settings.rate_limit_max_requests} requests per {settings.rate_limit_window} seconds allowed",
                "code": "RATE_LIMIT_EXCEEDED",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            },
            headers={
                "X-RateLimit-Limit": str(settings.rate_limit_max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + settings.rate_limit_window),
                "Retry-After": str(settings.rate_limit_window)
            }
        )
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Fail open - allow request if rate limiting fails
        return await call_next(request)


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """Request logging middleware."""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log response
        logger.info(
            f"Response: {response.status_code} "
            f"({process_time:.3f}s) for {request.method} {request.url.path}"
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"({process_time:.3f}s) - {str(e)}"
        )
        raise
