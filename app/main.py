"""Main FastAPI application."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.middleware import rate_limit_middleware, logging_middleware
from app.services.infrastructure.redis_service import redis_service
from app.services.infrastructure.storage_service import storage_service
from app.utils.exception_handlers import register_exception_handlers

# Import all routers from organized structure
from app.routes.core import system_router, auth_router, meta_router
from app.routes.videos import info_router, batch_router, concurrent_router as video_concurrent_router, files_router
from app.routes.streaming import proxy_router, direct_router
from app.routes.media import management_router, processing_router
from app.routes.legacy import simple_router, vrchat_router

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


# Register all routers in organized manner
def register_routers(app: FastAPI):
    """Register all API routers with the FastAPI application."""
    # Core system routers (health, system info, authentication, API metadata)
    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(meta_router)

    # Video operation routers
    app.include_router(info_router)
    app.include_router(files_router)
    app.include_router(batch_router)
    app.include_router(video_concurrent_router)

    # Streaming routers
    app.include_router(direct_router)
    app.include_router(proxy_router)

    # Media management routers
    app.include_router(management_router)
    app.include_router(processing_router)

    # Legacy routers (backward compatibility - registered last)
    app.include_router(simple_router)
    app.include_router(vrchat_router)


# Register all routers
register_routers(app)

# Register exception handlers
register_exception_handlers(app)


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
        from app.services.core.video_service import video_service
        stream_url = await video_service.get_stream_url(yt)
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
