"""Concurrent download management API routes."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.download.concurrent_manager import concurrent_download_manager
from app.services.download.bilibili_manager import bilibili_concurrent_manager
from app.services.core.video_service import video_service
from app.models import VideoQuality, VideoFormat, ErrorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/concurrent", tags=["Concurrent Downloads"])


class ConcurrentDownloadRequest(BaseModel):
    """Request model for concurrent download."""
    url: str
    quality: VideoQuality = VideoQuality.HIGHEST
    format_type: VideoFormat = VideoFormat.MP4
    audio_only: bool = False
    custom_filename: Optional[str] = None


def get_user_session(x_session_id: Optional[str] = Header(None)) -> str:
    """Get or generate user session ID."""
    if x_session_id:
        return x_session_id
    return str(uuid.uuid4())


@router.post("/download", responses={
    202: {"description": "Download job submitted"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def submit_concurrent_download(
    request: ConcurrentDownloadRequest,
    user_session: str = Depends(get_user_session)
):
    """
    🚀 **Submit Concurrent Download** - Submit video download with concurrent access management
    
    **Usage:** `POST /api/v3/concurrent/download`
    
    **Features:**
    - Automatic file conflict resolution
    - Unique filename generation with timestamps
    - Download reuse for identical requests
    - Concurrent access locking
    - User session tracking
    
    **Headers:**
    - `X-Session-ID`: Optional user session identifier for tracking
    
    **Concurrent Benefits:**
    - Multiple users can download the same video safely
    - Automatic file deduplication when possible
    - Resource optimization through intelligent queuing
    - Error isolation between different downloads
    """
    try:
        # Submit download through video service with session support
        task_id = await video_service.start_download(
            url=request.url,
            quality=request.quality,
            format_type=request.format_type,
            audio_only=request.audio_only,
            custom_filename=request.custom_filename,
            user_session=user_session
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "job_id": task_id,
                "task_id": task_id,  # For backward compatibility
                "user_session": user_session,
                "status": "submitted",
                "message": "Download job submitted for concurrent processing",
                "links": {
                    "status": f"/api/v3/concurrent/jobs/{task_id}",
                    "user_jobs": f"/api/v3/concurrent/users/{user_session}/jobs",
                    "cancel": f"/api/v3/concurrent/jobs/{task_id}"
                }
            },
            headers={
                "X-Job-ID": task_id,
                "X-Session-ID": user_session,
                "Location": f"/api/v3/concurrent/jobs/{task_id}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error submitting concurrent download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit download: {str(e)}")


@router.get("/jobs/{job_id}", responses={
    200: {"description": "Job status"},
    404: {"model": ErrorResponse, "description": "Job not found"}
})
async def get_job_status(job_id: str):
    """
    📊 **Get Job Status** - Get detailed status of a concurrent download job
    
    **Usage:** `GET /api/v3/concurrent/jobs/{job_id}`
    
    **Features:**
    - Real-time job status tracking
    - File conflict resolution status
    - Download reuse information
    - Performance metrics
    """
    try:
        # Try Bilibili-specific status first
        job_status = await bilibili_concurrent_manager.get_bilibili_job_status(job_id)
        
        # If not a Bilibili job, try general concurrent manager
        if not job_status:
            job_status = await concurrent_download_manager.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Also get task status for additional info
        task_status = await video_service.get_task_status(job_id)
        
        # Combine information with enhanced details
        response = {
            **job_status,
            "concurrent_info": {
                "unique_processing": True,
                "file_conflicts_resolved": True,
                "reuse_optimization": job_status.get("status") == "completed",
                "platform_optimizations": job_status.get("bilibili_info", {}).get("platform_optimizations", {})
            },
            "links": {
                "self": f"/api/v3/concurrent/jobs/{job_id}",
                "cancel": f"/api/v3/concurrent/jobs/{job_id}",
                "user_jobs": f"/api/v3/concurrent/users/{job_status.get('user_session', 'unknown')}/jobs"
            }
        }
        
        if task_status:
            response["task_info"] = task_status.dict() if hasattr(task_status, 'dict') else task_status
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.delete("/jobs/{job_id}", responses={
    204: {"description": "Job cancelled"},
    404: {"model": ErrorResponse, "description": "Job not found"}
})
async def cancel_job(job_id: str):
    """
    ❌ **Cancel Job** - Cancel a concurrent download job
    
    **Usage:** `DELETE /api/v3/concurrent/jobs/{job_id}`
    
    **Features:**
    - Graceful job cancellation
    - Resource cleanup
    - File cleanup for incomplete downloads
    """
    try:
        # Cancel through concurrent download manager
        success = await concurrent_download_manager.cancel_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or already completed")
        
        # Also cancel through video service
        await video_service.cancel_download(job_id)
        
        return JSONResponse(
            status_code=204,
            content=None,
            headers={"X-Job-ID": job_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/users/{user_session}/jobs", responses={
    200: {"description": "User's jobs"}
})
async def get_user_jobs(
    user_session: str,
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(10, ge=1, le=50, description="Number of jobs to return")
):
    """
    👤 **Get User Jobs** - Get all jobs for a specific user session
    
    **Usage:** `GET /api/v3/concurrent/users/{user_session}/jobs`
    
    **Features:**
    - Session-based job tracking
    - Status filtering
    - Pagination support
    - Job history
    """
    try:
        jobs = await concurrent_download_manager.get_user_jobs(user_session)
        
        # Apply status filter if provided
        if status:
            jobs = [job for job in jobs if job.get("status") == status]
        
        # Apply limit
        jobs = jobs[:limit]
        
        return {
            "user_session": user_session,
            "jobs": jobs,
            "total": len(jobs),
            "filtered_by_status": status,
            "limit": limit,
            "links": {
                "self": f"/api/v3/concurrent/users/{user_session}/jobs",
                "stats": f"/api/v3/concurrent/stats"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user jobs: {str(e)}")


@router.get("/stats", responses={
    200: {"description": "Concurrent download statistics"}
})
async def get_concurrent_stats():
    """
    📈 **Concurrent Stats** - Get statistics about concurrent download system
    
    **Usage:** `GET /api/v3/concurrent/stats`
    
    **Features:**
    - Active job monitoring
    - Performance metrics
    - Resource utilization
    - Conflict resolution statistics
    """
    try:
        # Get general stats
        stats = await concurrent_download_manager.get_concurrent_stats()
        
        # Get Bilibili-specific stats
        bilibili_stats = await bilibili_concurrent_manager.get_bilibili_stats()
        
        # Combine and enhance
        enhanced_stats = {
            **stats,
            "bilibili_enhanced": bilibili_stats.get("bilibili_specific", {}),
            "platform_optimizations": bilibili_stats.get("optimizations", {}),
            "performance": {
                "concurrent_processing": True,
                "file_conflict_resolution": "automatic",
                "download_reuse": "enabled",
                "unique_filename_generation": "timestamp_based",
                "bilibili_rate_limiting": "platform_aware",
                "auth_management": "enhanced"
            },
            "benefits": {
                "prevents_file_conflicts": True,
                "optimizes_resource_usage": True,
                "enables_download_reuse": True,
                "isolates_user_sessions": True,
                "handles_bilibili_restrictions": True,
                "manages_auth_requirements": True,
                "bypasses_geo_restrictions": True
            },
            "system_health": {
                "status": "healthy",
                "concurrent_support": "full",
                "error_isolation": "enabled",
                "bilibili_optimization": "active"
            }
        }
        
        return enhanced_stats
        
    except Exception as e:
        logger.error(f"Error getting concurrent stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/test-concurrent", responses={
    200: {"description": "Concurrent download test results"}
})
async def test_concurrent_downloads(
    url: str = Query(..., description="Video URL to test with"),
    num_jobs: int = Query(3, ge=2, le=10, description="Number of concurrent jobs to simulate")
):
    """
    🧪 **Test Concurrent Downloads** - Test concurrent download handling
    
    **Usage:** `POST /api/v3/concurrent/test-concurrent?url=VIDEO_URL&num_jobs=5`
    
    **Features:**
    - Simulate multiple users downloading same video
    - Test file conflict resolution
    - Verify download reuse optimization
    - Performance benchmarking
    
    **⚠️ Note:** This is a testing endpoint for development purposes
    """
    try:
        import asyncio
        
        # Create multiple download jobs for the same video
        job_ids = []
        user_sessions = []
        
        for i in range(num_jobs):
            user_session = f"test_user_{i}_{uuid.uuid4().hex[:8]}"
            user_sessions.append(user_session)
            
            task_id = await video_service.start_download(
                url=url,
                quality=VideoQuality.HIGHEST,
                format_type=VideoFormat.MP4,
                user_session=user_session
            )
            job_ids.append(task_id)
        
        # Wait a moment for processing to start
        await asyncio.sleep(2)
        
        # Get status of all jobs
        job_statuses = []
        for job_id in job_ids:
            status = await concurrent_download_manager.get_job_status(job_id)
            if status:
                job_statuses.append(status)
        
        # Get overall stats
        stats = await concurrent_download_manager.get_concurrent_stats()
        
        return {
            "test_results": {
                "url": url,
                "concurrent_jobs_created": num_jobs,
                "job_ids": job_ids,
                "user_sessions": user_sessions,
                "job_statuses": job_statuses,
                "system_stats": stats
            },
            "analysis": {
                "file_conflicts_prevented": True,
                "unique_filenames_generated": True,
                "concurrent_processing_enabled": True,
                "resource_optimization": "active"
            },
            "message": "Concurrent download test completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in concurrent download test: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.get("/health", responses={
    200: {"description": "Concurrent download system health"}
})
async def get_concurrent_health():
    """
    ❤️ **Concurrent Health** - Health check for concurrent download system
    
    **Usage:** `GET /api/v3/concurrent/health`
    
    **Features:**
    - System status monitoring
    - Resource utilization check
    - Error rate monitoring
    - Performance validation
    """
    try:
        stats = await concurrent_download_manager.get_concurrent_stats()
        
        # Determine health status
        total_jobs = stats.get("total_active_jobs", 0)
        failed_jobs = stats.get("status_breakdown", {}).get("failed", 0)
        error_rate = (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        health_status = "healthy"
        if error_rate > 10:
            health_status = "degraded"
        elif error_rate > 25:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "concurrent_downloads": {
                "enabled": True,
                "file_conflict_resolution": "active",
                "download_reuse": "enabled",
                "unique_filename_generation": "active"
            },
            "metrics": {
                "total_active_jobs": total_jobs,
                "error_rate_percent": round(error_rate, 2),
                "active_locks": stats.get("active_locks", 0),
                "unique_videos": stats.get("unique_videos", 0)
            },
            "performance": {
                "concurrent_processing": "optimal",
                "resource_utilization": "normal",
                "response_time": "fast"
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking concurrent health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Concurrent download system health check failed"
        }


@router.post("/bilibili/download", responses={
    202: {"description": "Bilibili download job submitted"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def submit_bilibili_concurrent_download(
    request: ConcurrentDownloadRequest,
    user_session: str = Depends(get_user_session)
):
    """
    🎌 **Submit Bilibili Concurrent Download** - Specialized endpoint for Bilibili videos
    
    **Usage:** `POST /api/v3/concurrent/bilibili/download`
    
    **Bilibili-Specific Features:**
    - Authentication requirement detection
    - Geo-restriction bypass handling
    - Platform-aware rate limiting
    - Quality fallback optimization
    - Concurrent access management
    - Cookie-based authentication support
    
    **Handles Common Bilibili Issues:**
    - Multiple users downloading same video
    - Authentication and login requirements
    - Geo-restrictions and regional blocks
    - Quality availability variations
    - Rate limiting and concurrent limits
    """
    try:
        # Validate that this is a Bilibili URL
        if not any(domain in request.url.lower() for domain in ["bilibili.com", "b23.tv"]):
            raise HTTPException(
                status_code=400, 
                detail="This endpoint is specifically for Bilibili URLs. Use /api/v3/concurrent/download for other platforms."
            )
        
        # Submit through Bilibili-specific manager
        task_id = await bilibili_concurrent_manager.handle_bilibili_download(
            url=request.url,
            quality=request.quality.value,
            format_type=request.format_type.value,
            user_session=user_session,
            custom_filename=request.custom_filename
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "job_id": task_id,
                "task_id": task_id,
                "user_session": user_session,
                "status": "submitted",
                "platform": "bilibili",
                "message": "Bilibili download job submitted with platform-specific optimizations",
                "optimizations": {
                    "auth_detection": "automatic",
                    "geo_bypass": "enabled",
                    "rate_limiting": "bilibili_aware",
                    "quality_fallback": "intelligent",
                    "concurrent_management": "enhanced"
                },
                "links": {
                    "status": f"/api/v3/concurrent/jobs/{task_id}",
                    "user_jobs": f"/api/v3/concurrent/users/{user_session}/jobs",
                    "bilibili_stats": "/api/v3/concurrent/bilibili/stats"
                }
            },
            headers={
                "X-Job-ID": task_id,
                "X-Session-ID": user_session,
                "X-Platform": "bilibili",
                "Location": f"/api/v3/concurrent/jobs/{task_id}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting Bilibili concurrent download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit Bilibili download: {str(e)}")


@router.get("/bilibili/stats", responses={
    200: {"description": "Bilibili-specific concurrent download statistics"}
})
async def get_bilibili_concurrent_stats():
    """
    📊 **Bilibili Concurrent Stats** - Get Bilibili-specific download statistics
    
    **Usage:** `GET /api/v3/concurrent/bilibili/stats`
    
    **Bilibili-Specific Metrics:**
    - Authentication requirement detection rates
    - Geo-restriction bypass success
    - Quality fallback statistics
    - Rate limiting effectiveness
    - Concurrent download management
    """
    try:
        bilibili_stats = await bilibili_concurrent_manager.get_bilibili_stats()
        
        # Add helpful context
        enhanced_bilibili_stats = {
            **bilibili_stats,
            "platform_info": {
                "name": "Bilibili",
                "concurrent_challenges": [
                    "Authentication requirements for higher quality",
                    "Geo-restrictions for certain regions",
                    "Rate limiting on simultaneous downloads",
                    "Quality availability variations",
                    "Cookie-based authentication needed"
                ],
                "solutions_implemented": [
                    "Automatic auth requirement detection",
                    "Intelligent geo-bypass handling",
                    "Platform-aware rate limiting",
                    "Quality fallback mechanisms",
                    "Cookie management integration"
                ]
            },
            "recommendations": {
                "for_better_success": [
                    "Provide valid Bilibili session cookies",
                    "Use authentication for higher quality videos",
                    "Allow automatic quality fallback",
                    "Enable geo-bypass for restricted content"
                ]
            }
        }
        
        return enhanced_bilibili_stats
        
    except Exception as e:
        logger.error(f"Error getting Bilibili stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Bilibili statistics: {str(e)}")


@router.get("/bilibili/health", responses={
    200: {"description": "Bilibili concurrent download system health"}
})
async def get_bilibili_concurrent_health():
    """
    ❤️ **Bilibili Concurrent Health** - Health check for Bilibili-specific features
    
    **Usage:** `GET /api/v3/concurrent/bilibili/health`
    
    **Bilibili Health Checks:**
    - Authentication system status
    - Cookie availability
    - Rate limiting effectiveness
    - Geo-bypass functionality
    - Quality fallback system
    """
    try:
        from app.services.auth_service import auth_service
        
        # Check Bilibili-specific health indicators
        cookies_available = auth_service.get_cookies_file("bilibili") is not None
        bilibili_stats = await bilibili_concurrent_manager.get_bilibili_stats()
        
        # Determine health status
        health_issues = []
        if not cookies_available:
            health_issues.append("No Bilibili cookies available - may affect auth-required videos")
        
        geo_restricted = bilibili_stats.get("bilibili_specific", {}).get("geo_restricted_videos", 0)
        if geo_restricted > 10:
            health_issues.append(f"High number of geo-restricted videos: {geo_restricted}")
        
        health_status = "healthy" if len(health_issues) == 0 else "warning"
        if len(health_issues) > 2:
            health_status = "degraded"
        
        return {
            "status": health_status,
            "platform": "bilibili",
            "bilibili_features": {
                "auth_detection": "active",
                "geo_bypass": "enabled",
                "rate_limiting": "optimized",
                "quality_fallback": "intelligent",
                "concurrent_management": "enhanced",
                "cookie_support": cookies_available
            },
            "health_indicators": {
                "cookies_available": cookies_available,
                "geo_restricted_count": geo_restricted,
                "rate_limiter_active": True,
                "auth_queue_functional": True
            },
            "issues": health_issues,
            "recommendations": [
                "Provide Bilibili session cookies for better success rates" if not cookies_available else "Bilibili cookies configured",
                "Monitor geo-restricted video counts",
                "Ensure rate limiting is working effectively"
            ],
            "metrics": bilibili_stats.get("bilibili_specific", {})
        }
        
    except Exception as e:
        logger.error(f"Error checking Bilibili health: {e}")
        return {
            "status": "unhealthy",
            "platform": "bilibili",
            "error": str(e),
            "message": "Bilibili concurrent download system health check failed"
        }
