"""Main FastAPI application."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.middleware import rate_limit_middleware, logging_middleware
from app.routes import videos, files, system
from app.services.redis_service import redis_service
from app.services.storage_service import storage_service
from app.exceptions import (
    APIException, RateLimitExceededError, StorageLimitExceededError,
    ValidationError, UnsupportedURLError, VideoNotFoundError,
    DownloadError, TaskNotFoundError, ServiceUnavailableError
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting YouTuberBilBiliHelper API...")
    
    # Test Redis connection
    try:
        await redis_service.get_pool()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    
    # Start background tasks
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    logger.info("Shutting down YouTuberBilBiliHelper API...")
    cleanup_task.cancel()
    await redis_service.close()


async def periodic_cleanup():
    """Periodic cleanup task."""
    while True:
        try:
            await asyncio.sleep(settings.cleanup_interval)
            logger.info("Running periodic cleanup...")
            await storage_service.cleanup_expired_files()
            await storage_service.ensure_storage_available()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Periodic cleanup error: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "HEAD"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(logging_middleware)

# Include routers
app.include_router(videos.router)
app.include_router(files.router)
app.include_router(system.router)

# Include new streaming router
from app.routes import streaming
app.include_router(streaming.router)

# Include authentication router
from app.routes import auth
app.include_router(auth.router)

# Include simple/user-friendly router (highest priority)
from app.routes import simple
app.include_router(simple.router)

# Include VRChat-optimized router
from app.routes import vrchat
app.include_router(vrchat.router)

# Include enhanced API v3 routers
from app.routes import meta, videos_v3, streaming_v3, concurrent
app.include_router(meta.router)
app.include_router(videos_v3.router)
app.include_router(streaming_v3.router)
app.include_router(concurrent.router)

# Include new enterprise-grade media management routers
from app.routes import media_management, content_processing
app.include_router(media_management.router)
app.include_router(content_processing.router)


# Exception handlers
@app.exception_handler(APIException)
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


@app.exception_handler(RateLimitExceededError)
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


@app.exception_handler(StorageLimitExceededError)
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


@app.exception_handler(ValidationError)
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


@app.exception_handler(UnsupportedURLError)
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


@app.exception_handler(VideoNotFoundError)
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


@app.exception_handler(TaskNotFoundError)
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


@app.exception_handler(ServiceUnavailableError)
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


@app.exception_handler(HTTPException)
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


@app.exception_handler(Exception)
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


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "health_url": "/api/health",
        "media_endpoints": {
            "content_analysis": "/api/media/details?url=CONTENT_URL",
            "format_conversion": "/api/media/format/convert?url=CONTENT_URL&target_quality=720p",
            "batch_processing": "/api/content/process/queue?source_url=CONTENT_URL",
            "performance_analytics": "/api/content/analytics/performance"
        },
        "examples": {
            "media_analysis": "/api/media/details?url=https://example.com/content&include_formats=true",
            "content_optimization": "/api/content/stream/optimize?source=platform/content_id&quality=high",
            "format_discovery": "/api/media/format/available?url=https://example.com/content"
        },
        "supported_platforms": ["Major Video Platforms", "Social Media Platforms", "Live Streaming Services", "Educational Platforms"],
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }


# Legacy v1 endpoints for backward compatibility
@app.get("/api/v1/", tags=["legacy"])
async def legacy_raw_link(yt: str):
    """Legacy endpoint for raw video links."""
    try:
        from app.services.video_service import video_service
        stream_url = await video_service.get_stream_url(yt)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=stream_url, status_code=302)
    except Exception as e:
        logger.error(f"Legacy endpoint error: {e}")
        raise HTTPException(status_code=400, detail="Invalid or missing video URL")


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.api_title,
        version=settings.api_version,
        description=f"""
        {settings.api_description}
        
        ## Features
        
        - **Video Downloads**: Download videos from YouTube and BiliBili
        - **Streaming**: Get direct stream URLs or proxy streams
        - **Batch Operations**: Download multiple videos at once
        - **Task Management**: Track download progress and status
        - **Storage Management**: Automatic cleanup and storage limits
        - **Rate Limiting**: Configurable rate limiting per client
        - **Health Monitoring**: System health and statistics endpoints
        
        ## Supported Platforms
        
        - YouTube (youtube.com, youtu.be)
        - BiliBili (bilibili.com, b23.tv)
        
        ## Rate Limits
        
        - **Default**: {settings.rate_limit_max_requests} requests per {settings.rate_limit_window} seconds
        - **Headers**: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        
        ## Storage
        
        - **Automatic Cleanup**: Files older than {settings.temp_file_retention_hours} hours
        - **Storage Limit**: {settings.max_storage_gb} GB maximum
        - **Formats**: MP4, WebM, MKV, MP3, M4A
        """,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
