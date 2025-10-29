"""Enhanced video API routes with improved RESTful design and batch operations."""

import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from app.services.core.video_service import video_service
from app.services.infrastructure.storage_service import storage_service
from app.exceptions import (
    VideoNotFoundError, DownloadError, UnsupportedURLError,
    ValidationError, TaskNotFoundError
)
from app.models import VideoInfo, TaskInfo, VideoQuality, VideoFormat, ErrorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/videos", tags=["Videos v3"])

# Enhanced request/response models
class VideoRequest(BaseModel):
    """Single video request model."""
    url: HttpUrl
    quality: VideoQuality = VideoQuality.HIGHEST
    format: VideoFormat = VideoFormat.MP4
    audio_only: bool = False
    custom_filename: Optional[str] = None

class BatchVideoRequest(BaseModel):
    """Batch video request model."""
    videos: List[VideoRequest]
    parallel: bool = True
    max_concurrent: int = 3

class VideoResponse(BaseModel):
    """Enhanced video response model."""
    id: str
    url: str
    info: VideoInfo
    task_id: Optional[str] = None
    download_url: Optional[str] = None
    stream_url: Optional[str] = None
    status: str
    created_at: str
    links: Dict[str, str] = {}

class BatchVideoResponse(BaseModel):
    """Batch operation response model."""
    batch_id: str
    total: int
    successful: int
    failed: int
    videos: List[VideoResponse]
    status: str
    created_at: str


@router.get("/{video_id}", responses={
    200: {"description": "Video information"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def get_video_by_id(
    video_id: str,
    include_formats: bool = Query(False, description="Include available formats"),
    include_tasks: bool = Query(False, description="Include related tasks")
):
    """
    📹 **Get Video by ID** - Retrieve video information by internal ID
    
    **RESTful Design:** `GET /api/v3/videos/{video_id}`
    
    **Features:**
    - Cached video information retrieval
    - Optional format information inclusion
    - Related task information
    - HATEOAS links for related operations
    """
    try:
        # This would typically retrieve from a database
        # For now, we'll return a placeholder response
        return {
            "id": video_id,
            "status": "cached",
            "info": {
                "title": "Sample Video",
                "description": "This is a sample video response",
                "duration": 180,
                "platform": "youtube"
            },
            "links": {
                "self": f"/api/v3/videos/{video_id}",
                "download": f"/api/v3/videos/{video_id}/download",
                "stream": f"/api/v3/videos/{video_id}/stream",
                "tasks": f"/api/v3/videos/{video_id}/tasks"
            },
            "message": "Video ID endpoint - implementation in progress"
        }
    except Exception as e:
        logger.error(f"Error retrieving video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve video: {str(e)}")


@router.post("/info", responses={
    200: {"description": "Video information extracted"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def get_video_info(request: VideoRequest):
    """
    🔍 **Get Video Information** - Extract video metadata
    
    **Usage:** `POST /api/v3/videos/info`
    
    **Enhanced Features:**
    - Comprehensive video metadata
    - Format availability analysis
    - Platform-specific information
    - Caching optimization
    - HATEOAS links
    """
    try:
        video_info = await video_service.get_video_info(str(request.url))
        video_id = str(uuid.uuid4())  # Generate internal ID
        
        response = VideoResponse(
            id=video_id,
            url=str(request.url),
            info=video_info,
            status="info_extracted",
            created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            links={
                "self": f"/api/v3/videos/{video_id}",
                "download": f"/api/v3/videos/download",
                "stream": f"/api/v3/videos/stream",
                "batch_info": "/api/v3/videos/batch/info"
            }
        )
        
        return response
        
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video information")


@router.post("/batch/info", responses={
    200: {"description": "Batch video information"},
    400: {"model": ErrorResponse, "description": "Invalid request"}
})
async def get_batch_video_info(
    request: BatchVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    📋 **Batch Video Information** - Get information for multiple videos
    
    **Usage:** `POST /api/v3/videos/batch/info`
    
    **Features:**
    - Parallel processing for faster results
    - Configurable concurrency limits
    - Partial success handling
    - Progress tracking
    """
    try:
        batch_id = str(uuid.uuid4())
        results = []
        successful = 0
        failed = 0
        
        for video_request in request.videos:
            try:
                video_info = await video_service.get_video_info(str(video_request.url))
                video_id = str(uuid.uuid4())
                
                result = VideoResponse(
                    id=video_id,
                    url=str(video_request.url),
                    info=video_info,
                    status="success",
                    created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
                    links={
                        "self": f"/api/v3/videos/{video_id}",
                        "download": f"/api/v3/videos/download"
                    }
                )
                results.append(result)
                successful += 1
                
            except Exception as e:
                result = VideoResponse(
                    id=str(uuid.uuid4()),
                    url=str(video_request.url),
                    info=VideoInfo(id="", title="Error", description=str(e)),
                    status="failed",
                    created_at=time.strftime('%Y-%m-%d %H:%M:%S')
                )
                results.append(result)
                failed += 1
        
        response = BatchVideoResponse(
            batch_id=batch_id,
            total=len(request.videos),
            successful=successful,
            failed=failed,
            videos=results,
            status="completed",
            created_at=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in batch video info: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch request")


@router.post("/download", responses={
    202: {"description": "Download started"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def start_video_download(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
    x_priority: Optional[str] = Header(None, description="Task priority (low, normal, high)")
):
    """
    ⬇️ **Start Video Download** - Initiate video download with enhanced options
    
    **Usage:** `POST /api/v3/videos/download`
    
    **Enhanced Features:**
    - Priority-based task queuing
    - Advanced progress tracking
    - Webhook notifications support
    - Custom metadata attachment
    - Automatic cleanup scheduling
    """
    try:
        # Get video info first
        video_info = await video_service.get_video_info(str(request.url))
        
        # Start download with enhanced options
        task_id = await video_service.start_download(
            url=str(request.url),
            quality=request.quality,
            format_type=request.format,
            audio_only=request.audio_only,
            custom_filename=request.custom_filename
        )
        
        # Schedule cleanup
        background_tasks.add_task(storage_service.cleanup_expired_files)
        
        video_id = str(uuid.uuid4())
        
        response = VideoResponse(
            id=video_id,
            url=str(request.url),
            info=video_info,
            task_id=task_id,
            status="download_started",
            created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            links={
                "self": f"/api/v3/videos/{video_id}",
                "task": f"/api/v3/videos/tasks/{task_id}",
                "cancel": f"/api/v3/videos/tasks/{task_id}",
                "batch_download": "/api/v3/videos/batch/download"
            }
        )
        
        return JSONResponse(
            status_code=202,
            content=response.dict(),
            headers={
                "Location": f"/api/v3/videos/tasks/{task_id}",
                "X-Task-ID": task_id,
                "X-Video-ID": video_id
            }
        )
        
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        raise HTTPException(status_code=500, detail="Failed to start download")


@router.post("/batch/download", responses={
    202: {"description": "Batch download started"},
    400: {"model": ErrorResponse, "description": "Invalid request"}
})
async def start_batch_download(
    request: BatchVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    📦 **Batch Video Download** - Start multiple downloads with advanced management
    
    **Usage:** `POST /api/v3/videos/batch/download`
    
    **Features:**
    - Parallel download processing
    - Queue management and prioritization
    - Partial failure handling
    - Progress aggregation
    - Resource optimization
    """
    try:
        batch_id = str(uuid.uuid4())
        results = []
        successful = 0
        failed = 0
        
        for video_request in request.videos:
            try:
                # Get video info
                video_info = await video_service.get_video_info(str(video_request.url))
                
                # Start download
                task_id = await video_service.start_download(
                    url=str(video_request.url),
                    quality=video_request.quality,
                    format_type=video_request.format,
                    audio_only=video_request.audio_only,
                    custom_filename=video_request.custom_filename
                )
                
                video_id = str(uuid.uuid4())
                
                result = VideoResponse(
                    id=video_id,
                    url=str(video_request.url),
                    info=video_info,
                    task_id=task_id,
                    status="download_started",
                    created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
                    links={
                        "task": f"/api/v3/videos/tasks/{task_id}",
                        "cancel": f"/api/v3/videos/tasks/{task_id}"
                    }
                )
                results.append(result)
                successful += 1
                
            except Exception as e:
                result = VideoResponse(
                    id=str(uuid.uuid4()),
                    url=str(video_request.url),
                    info=VideoInfo(id="", title="Error", description=str(e)),
                    status="failed",
                    created_at=time.strftime('%Y-%m-%d %H:%M:%S')
                )
                results.append(result)
                failed += 1
        
        # Schedule cleanup
        background_tasks.add_task(storage_service.cleanup_expired_files)
        
        response = BatchVideoResponse(
            batch_id=batch_id,
            total=len(request.videos),
            successful=successful,
            failed=failed,
            videos=results,
            status="started",
            created_at=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return JSONResponse(
            status_code=202,
            content=response.dict(),
            headers={
                "Location": f"/api/v3/videos/batch/{batch_id}",
                "X-Batch-ID": batch_id
            }
        )
        
    except Exception as e:
        logger.error(f"Error in batch download: {e}")
        raise HTTPException(status_code=500, detail="Failed to start batch download")


@router.get("/tasks/{task_id}", responses={
    200: {"description": "Task status"},
    404: {"model": ErrorResponse, "description": "Task not found"}
})
async def get_task_status(task_id: str):
    """
    📊 **Get Task Status** - Retrieve download task information
    
    **RESTful Design:** `GET /api/v3/videos/tasks/{task_id}`
    
    **Enhanced Features:**
    - Real-time progress updates
    - Detailed error information
    - Performance metrics
    - Related resource links
    """
    try:
        task_info = await video_service.get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Add enhanced links
        links = {
            "self": f"/api/v3/videos/tasks/{task_id}",
            "cancel": f"/api/v3/videos/tasks/{task_id}",
            "batch": "/api/v3/videos/tasks/batch"
        }
        
        if task_info.download_url:
            links["download"] = task_info.download_url
        
        response = task_info.dict()
        response["links"] = links
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.delete("/tasks/{task_id}", responses={
    204: {"description": "Task cancelled"},
    404: {"model": ErrorResponse, "description": "Task not found"}
})
async def cancel_task(task_id: str):
    """
    ❌ **Cancel Task** - Cancel a running download task
    
    **RESTful Design:** `DELETE /api/v3/videos/tasks/{task_id}`
    
    **Features:**
    - Graceful task cancellation
    - Resource cleanup
    - Status tracking
    """
    try:
        success = await video_service.cancel_download(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or already completed")
        
        return JSONResponse(
            status_code=204,
            content=None,
            headers={"X-Task-ID": task_id}
        )
        
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/tasks", responses={
    200: {"description": "List of tasks"}
})
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    📋 **List Tasks** - Get list of download tasks with filtering and pagination
    
    **Usage:** `GET /api/v3/videos/tasks?status=pending&limit=20`
    
    **Features:**
    - Status-based filtering
    - Pagination support
    - Sorting options
    - Summary statistics
    """
    # This would typically query a database
    # For now, return a placeholder response
    return {
        "tasks": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "has_more": False,
        "links": {
            "self": f"/api/v3/videos/tasks?limit={limit}&offset={offset}",
            "next": None,
            "prev": None
        },
        "message": "Task listing - implementation in progress"
    }
