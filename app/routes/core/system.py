"""System and health monitoring routes."""

import time
import psutil
from fastapi import APIRouter, HTTPException
from app.models import HealthResponse, StorageInfo, ErrorResponse
from app.config import settings
from app.services.redis_service import redis_service
from app.services.storage_service import storage_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/system", tags=["system"])


@router.get("/health", response_model=HealthResponse, responses={
    500: {"model": ErrorResponse, "description": "Service unhealthy"}
})
async def health_check() -> HealthResponse:
    """Comprehensive health check."""
    try:
        # Check Redis
        redis_health = await redis_service.get_health()
        
        # Check storage
        storage_info = await storage_service.get_storage_info()
        
        # Check system resources
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        services = {
            "redis": redis_health.get("status", "unknown"),
            "storage": "healthy" if storage_info.available_space_gb > 1 else "warning",
            "memory": "healthy" if memory.percent < 90 else "warning",
            "disk": "healthy" if disk.percent < 90 else "warning"
        }
        
        # Overall status
        overall_status = "healthy"
        if any(status == "unhealthy" for status in services.values()):
            overall_status = "unhealthy"
        elif any(status == "warning" for status in services.values()):
            overall_status = "warning"
        
        return HealthResponse(
            status=overall_status,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            version=settings.api_version,
            services=services,
            storage={
                "used_gb": storage_info.used_space_gb,
                "available_gb": storage_info.available_space_gb,
                "total_gb": storage_info.total_space_gb,
                "file_count": storage_info.file_count,
                "memory_usage_percent": memory.percent,
                "disk_usage_percent": disk.percent
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/storage", response_model=StorageInfo, responses={
    500: {"model": ErrorResponse, "description": "Failed to get storage info"}
})
async def get_storage_info() -> StorageInfo:
    """Get detailed storage information."""
    try:
        return await storage_service.get_storage_info()
    except Exception as e:
        logger.error(f"Error getting storage info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage information")


@router.post("/storage/cleanup", responses={
    200: {"description": "Cleanup completed"},
    500: {"model": ErrorResponse, "description": "Cleanup failed"}
})
async def cleanup_storage():
    """Manually trigger storage cleanup."""
    try:
        await storage_service.cleanup_expired_files()
        await storage_service.ensure_storage_available()
        return {"message": "Storage cleanup completed successfully"}
    except Exception as e:
        logger.error(f"Storage cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Storage cleanup failed")


@router.get("/stats", responses={
    200: {"description": "System statistics"},
    500: {"model": ErrorResponse, "description": "Failed to get stats"}
})
async def get_system_stats():
    """Get system statistics."""
    try:
        # System info
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # Storage info
        storage_info = await storage_service.get_storage_info()
        
        # Redis info
        redis_health = await redis_service.get_health()
        
        return {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "storage": storage_info.dict(),
            "redis": redis_health,
            "config": {
                "max_storage_gb": settings.max_storage_gb,
                "rate_limit_max_requests": settings.rate_limit_max_requests,
                "rate_limit_window": settings.rate_limit_window,
                "max_concurrent_downloads": settings.max_concurrent_downloads
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system statistics")


@router.get("/version", responses={
    200: {"description": "API version information"}
})
async def get_version():
    """Get API version and build information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
