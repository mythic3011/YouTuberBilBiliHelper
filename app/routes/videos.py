"""Video-related API routes."""

import time
from typing import List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import RedirectResponse, StreamingResponse
import aiohttp
from app.models import (
    DownloadRequest, DownloadResponse, StreamRequest, StreamResponse,
    VideoInfo, TaskInfo, BatchDownloadRequest, BatchDownloadResponse,
    ErrorResponse
)
from app.services.video_service import video_service
from app.services.storage_service import storage_service
from app.exceptions import (
    VideoNotFoundError, DownloadError, UnsupportedURLError,
    ValidationError, TaskNotFoundError
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/videos", tags=["videos"])


@router.post("/info", response_model=VideoInfo, responses={
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def get_video_info(request: DownloadRequest) -> VideoInfo:
    """Get video information without downloading."""
    try:
        return await video_service.get_video_info(str(request.url))
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video information")


@router.post("/download", response_model=DownloadResponse, responses={
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def download_video(
    request: DownloadRequest,
    background_tasks: BackgroundTasks
) -> DownloadResponse:
    """Start video download and return task ID."""
    try:
        # Get video info first
        video_info = await video_service.get_video_info(str(request.url))
        
        # Start download
        task_id = await video_service.start_download(
            url=str(request.url),
            quality=request.quality,
            format_type=request.format,
            audio_only=request.audio_only,
            custom_filename=request.custom_filename
        )
        
        # Schedule storage cleanup
        background_tasks.add_task(storage_service.cleanup_expired_files)
        
        return DownloadResponse(
            task_id=task_id,
            status="pending",
            message="Download started",
            video_info=video_info
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


@router.post("/batch-download", response_model=BatchDownloadResponse, responses={
    400: {"model": ErrorResponse, "description": "Invalid request"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def batch_download_videos(
    request: BatchDownloadRequest,
    background_tasks: BackgroundTasks
) -> BatchDownloadResponse:
    """Start batch video downloads."""
    try:
        tasks = []
        batch_id = f"batch_{int(time.time())}"
        
        for url in request.urls:
            try:
                # Get video info
                video_info = await video_service.get_video_info(str(url))
                
                # Start download
                task_id = await video_service.start_download(
                    url=str(url),
                    quality=request.quality,
                    format_type=request.format,
                    audio_only=request.audio_only
                )
                
                tasks.append(DownloadResponse(
                    task_id=task_id,
                    status="pending",
                    message="Download started",
                    video_info=video_info
                ))
                
            except Exception as e:
                logger.warning(f"Failed to start download for {url}: {e}")
                tasks.append(DownloadResponse(
                    task_id="",
                    status="failed",
                    message=f"Failed to start download: {str(e)}"
                ))
        
        # Schedule storage cleanup
        background_tasks.add_task(storage_service.cleanup_expired_files)
        
        return BatchDownloadResponse(
            batch_id=batch_id,
            total_count=len(request.urls),
            tasks=tasks
        )
        
    except Exception as e:
        logger.error(f"Error in batch download: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch download")


@router.get("/tasks/{task_id}", response_model=TaskInfo, responses={
    404: {"model": ErrorResponse, "description": "Task not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def get_task_status(task_id: str) -> TaskInfo:
    """Get download task status."""
    try:
        task_info = await video_service.get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_info
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.delete("/tasks/{task_id}", responses={
    200: {"description": "Task cancelled successfully"},
    404: {"model": ErrorResponse, "description": "Task not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def cancel_download(task_id: str):
    """Cancel active download."""
    try:
        success = await video_service.cancel_download(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or already completed")
        return {"message": "Download cancelled successfully"}
    except Exception as e:
        logger.error(f"Error cancelling download: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel download")


@router.post("/stream", response_model=StreamResponse, responses={
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def get_stream_info(request: StreamRequest) -> StreamResponse:
    """Get video stream information."""
    try:
        video_info = await video_service.get_video_info(str(request.url))
        stream_url = await video_service.get_stream_url(str(request.url), request.quality)
        
        return StreamResponse(
            stream_url=stream_url,
            video_info=video_info,
            expires_at=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() + 3600))
        )
        
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting stream info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stream information")


@router.get("/stream-proxy", responses={
    200: {"description": "Video stream"},
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def stream_video_proxy(url: str, quality: str = "highest"):
    """Proxy video stream directly."""
    try:
        # Validate quality parameter
        try:
            quality_enum = {
                "highest": video_service.VideoQuality.HIGHEST,
                "lowest": video_service.VideoQuality.LOWEST,
                "best_audio": video_service.VideoQuality.BEST_AUDIO,
                "best_video": video_service.VideoQuality.BEST_VIDEO
            }.get(quality, video_service.VideoQuality.HIGHEST)
        except (KeyError, AttributeError) as e:
            logger.debug(f"Invalid quality parameter '{quality}', using highest: {e}")
            quality_enum = video_service.VideoQuality.HIGHEST
        
        stream_url = await video_service.get_stream_url(url, quality_enum)
        
        # Stream the video content
        async with aiohttp.ClientSession() as session:
            async with session.get(stream_url) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', 'video/mp4')
                    content_length = response.headers.get('content-length')
                    
                    headers = {"Content-Type": content_type}
                    if content_length:
                        headers["Content-Length"] = content_length
                    
                    async def stream_content():
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                    
                    return StreamingResponse(
                        stream_content(),
                        media_type=content_type,
                        headers=headers
                    )
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to fetch video stream"
                    )
                    
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error streaming video: {e}")
        raise HTTPException(status_code=500, detail="Failed to stream video")


@router.get("/redirect", responses={
    302: {"description": "Redirect to video stream"},
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def redirect_to_stream(url: str, quality: str = "highest"):
    """Redirect to direct video stream URL."""
    try:
        # Validate quality parameter
        try:
            quality_enum = {
                "highest": video_service.VideoQuality.HIGHEST,
                "lowest": video_service.VideoQuality.LOWEST,
                "best_audio": video_service.VideoQuality.BEST_AUDIO,
                "best_video": video_service.VideoQuality.BEST_VIDEO
            }.get(quality, video_service.VideoQuality.HIGHEST)
        except (KeyError, AttributeError) as e:
            logger.debug(f"Invalid quality parameter '{quality}', using highest: {e}")
            quality_enum = video_service.VideoQuality.HIGHEST
        
        stream_url = await video_service.get_stream_url(url, quality_enum)
        return RedirectResponse(url=stream_url, status_code=302)
        
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error redirecting to stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stream URL")


@router.get("/download/vrchat", responses={
    302: {"description": "Redirect to optimized download"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def download_video_vrchat_get(
    url: str = Query(..., description="Video URL from any supported platform"),
    quality: str = Query("best", description="Video quality (best, 720p, 480p, 360p)"),
    player: str = Query("auto", description="Unity player type optimization (avpro, unity, auto)"),
    filename: str = Query(None, description="Custom filename (optional)")
):
    """
    VRChat-optimized video download with Unity player compatibility (GET method only).
    
    **GET-only for VRChat compatibility** - VRChat video players only support GET requests.
    
    **Usage:**
    - `GET /api/v2/videos/download/vrchat?url=https://youtube.com/watch?v=VIDEO_ID`
    - `GET /api/v2/videos/download/vrchat?url=https://youtu.be/VIDEO_ID&quality=720p&player=avpro`
    
    **VRChat & Unity Optimizations:**
    - Safe filename sanitization (removes apostrophes and special chars)
    - MP4 format prioritization for better compatibility
    - Enhanced error handling for VRChat-specific issues
    - Unity player-specific codec optimization (AVPro Video, Unity Video Player)
    
    **Player Options:**
    - `avpro` - AVPro Video optimized (H.264 baseline, AAC audio)
    - `unity` - Unity Video Player optimized (broader codec support)
    - `auto` - Automatic detection based on format availability
    
    **Returns:** Redirect to streaming proxy with download headers
    """
    try:
        # Validate URL format
        from app.routes.simple import extract_video_id_from_url
        platform, video_id = extract_video_id_from_url(url)
        
        # Generate VRChat-compatible filename if not provided
        if not filename:
            try:
                # Get video info for filename generation
                video_info = await video_service.get_video_info(url)
                title = video_info.title or f"{platform}_{video_id}"
                # Use VRChat-compatible filename sanitization
                safe_title = video_service._sanitize_filename_for_vrchat(title)
                filename = f"{safe_title}.mp4"
            except Exception as e:
                logger.debug(f"Could not get video info for filename: {e}")
                filename = f"{platform}_{video_id}_vrchat.mp4"
        
        # Map quality parameter for VRChat compatibility
        quality_map = {
            "best": "highest",
            "720p": "720p", 
            "480p": "480p",
            "360p": "360p"
        }
        mapped_quality = quality_map.get(quality, "720p")  # Default to 720p for VRChat
        
        # Redirect to streaming proxy with VRChat-optimized parameters
        proxy_url = f"/api/v2/stream/proxy/{platform}/{video_id}"
        params = f"?quality={mapped_quality}&download=true&filename={filename}&player={player}"
        
        return RedirectResponse(url=proxy_url + params, status_code=302)
        
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing VRChat download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process VRChat download: {str(e)}")
