"""Centralized exception handlers for the API."""

import logging
import time
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.exceptions import (
    APIException, RateLimitExceededError, StorageLimitExceededError,
    ValidationError, UnsupportedURLError, VideoNotFoundError,
    DownloadError, TaskNotFoundError, ServiceUnavailableError
)
from app.config import settings

logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions."""
    logger.error(f"API Exception: {exc.message} - {exc.detail}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError):
    """Handle rate limit exceptions."""
    return JSONResponse(
        status_code=429,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        },
        headers={
            "Retry-After": str(settings.rate_limit_window)
        }
    )


async def storage_limit_exception_handler(request: Request, exc: StorageLimitExceededError):
    """Handle storage limit exceptions."""
    return JSONResponse(
        status_code=507,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def unsupported_url_exception_handler(request: Request, exc: UnsupportedURLError):
    """Handle unsupported URL exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def video_not_found_exception_handler(request: Request, exc: VideoNotFoundError):
    """Handle video not found exceptions."""
    return JSONResponse(
        status_code=404,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def task_not_found_exception_handler(request: Request, exc: TaskNotFoundError):
    """Handle task not found exceptions."""
    return JSONResponse(
        status_code=404,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableError):
    """Handle service unavailable exceptions."""
    return JSONResponse(
        status_code=503,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "code": exc.code,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    logger.error(f"HTTP Exception: {exc.detail} (status_code={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_exception_handler)
    app.add_exception_handler(StorageLimitExceededError, storage_limit_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(UnsupportedURLError, unsupported_url_exception_handler)
    app.add_exception_handler(VideoNotFoundError, video_not_found_exception_handler)
    app.add_exception_handler(TaskNotFoundError, task_not_found_exception_handler)
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

