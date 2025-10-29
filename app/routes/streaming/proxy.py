"""Enhanced streaming routes focused on proxy functionality."""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query, Response
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from app.models import ErrorResponse
from app.services.streaming import streaming_service
from app.exceptions import VideoNotFoundError, ServiceUnavailableError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/stream", tags=["streaming"])


@router.get("/direct/{platform}/{video_id}", responses={
    302: {"description": "Redirect to direct stream URL"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    503: {"model": ErrorResponse, "description": "Service unavailable"}
})
async def get_direct_stream_url(
    platform: str,
    video_id: str,
    quality: str = Query(default="best", description="Video quality (best, 1080p, 720p, 480p, worst)"),
    format: str = Query(default="mp4", description="Video format preference"),
    no_cache: bool = Query(default=False, description="Bypass cache")
):
    """Get direct stream URL with redirect (fastest option)."""
    try:
        stream_data = await streaming_service.get_stream_url(
            platform=platform,
            video_id=video_id,
            quality=quality,
            use_cache=not no_cache
        )
        
        # Set appropriate headers for the redirect
        headers = {
            "Cache-Control": f"public, max-age={settings.cache_max_age}",
            "X-Platform": platform,
            "X-Quality": quality,
            "X-Video-Title": stream_data.get("video_info", {}).get("title", "")[:100]
        }
        
        return RedirectResponse(
            url=stream_data["stream_url"],
            status_code=302,
            headers=headers
        )
        
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Direct stream error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stream URL")


@router.get("/proxy/{platform}/{video_id}", responses={
    200: {"description": "Proxied video stream"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"},
    503: {"model": ErrorResponse, "description": "Service unavailable"}
})
async def proxy_video_stream(
    platform: str,
    video_id: str,
    quality: str = Query(default="best", description="Video quality"),
    format: str = Query(default="mp4", description="Video format preference"),
    download: bool = Query(default=False, description="Add download headers"),
    filename: Optional[str] = Query(None, description="Custom filename for download")
):
    """Proxy video stream through our server (for CORS/embedding)."""
    try:
        # Get streaming headers
        headers = await streaming_service.get_streaming_headers(platform)
        
        # Add download headers if requested
        if download:
            if not filename:
                filename = f"{platform}_{video_id}.mp4"
            
            # Properly encode filename for Content-Disposition header
            # Use RFC 5987 encoding for Unicode filenames
            import urllib.parse
            try:
                # Try ASCII first (fastest)
                filename.encode('ascii')
                headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            except UnicodeEncodeError:
                # Use RFC 5987 encoding for Unicode filenames
                encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
                headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
            
            headers['Content-Description'] = 'File Transfer'
        
        # Create streaming response
        return StreamingResponse(
            streaming_service.proxy_video_stream(platform, video_id, quality),
            media_type=headers["Content-Type"],
            headers=headers
        )
        
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Proxy stream error: {e}")
        raise HTTPException(status_code=500, detail="Failed to proxy stream")


@router.get("/auto/{platform}/{video_id}", responses={
    302: {"description": "Adaptive quality stream URL"},
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def get_adaptive_stream(
    request: Request,
    platform: str,
    video_id: str,
    bandwidth: Optional[int] = Query(default=None, description="Client bandwidth in kbps"),
    device: str = Query(default="desktop", description="Device type (mobile, tablet, desktop)")
):
    """Get adaptively selected stream URL based on client capabilities."""
    try:
        # Auto-detect bandwidth from User-Agent if not provided
        user_agent = request.headers.get("user-agent", "").lower()
        if device == "auto":
            if "mobile" in user_agent:
                device = "mobile"
            elif "tablet" in user_agent:
                device = "tablet"
            else:
                device = "desktop"
        
        stream_data = await streaming_service.get_adaptive_stream_url(
            platform=platform,
            video_id=video_id,
            bandwidth_kbps=bandwidth,
            device_type=device
        )
        
        headers = {
            "Cache-Control": f"public, max-age={settings.cache_max_age}",
            "X-Platform": platform,
            "X-Selected-Quality": stream_data.get("quality", "unknown"),
            "X-Device-Type": device
        }
        
        return RedirectResponse(
            url=stream_data["stream_url"],
            status_code=302,
            headers=headers
        )
        
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Adaptive stream error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get adaptive stream")


@router.get("/info/{platform}/{video_id}", responses={
    200: {"description": "Stream information"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def get_stream_info(
    platform: str,
    video_id: str,
    quality: str = Query(default="best", description="Video quality")
):
    """Get stream information without redirecting."""
    try:
        stream_data = await streaming_service.get_stream_url(platform, video_id, quality)
        
        # Return detailed information
        return {
            "platform": platform,
            "video_id": video_id,
            "stream_url": stream_data["stream_url"],
            "quality": stream_data.get("quality"),
            "video_info": stream_data.get("video_info", {}),
            "expires_at": stream_data.get("expires_at"),
            "cached_at": stream_data.get("cached_at"),
            "timestamp": time.time()
        }
        
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Stream info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stream info")


@router.post("/batch", responses={
    200: {"description": "Batch stream URLs"},
    400: {"model": ErrorResponse, "description": "Invalid request"}
})
async def get_batch_streams(requests: list[dict]):
    """Get multiple stream URLs efficiently."""
    try:
        if len(requests) > 50:  # Reasonable limit
            raise HTTPException(status_code=400, detail="Too many requests (max 50)")
        
        # Validate requests
        valid_requests = []
        for req in requests:
            if "platform" in req and "video_id" in req:
                valid_requests.append({
                    "platform": req["platform"],
                    "video_id": req["video_id"],
                    "quality": req.get("quality", "best")
                })
        
        if not valid_requests:
            raise HTTPException(status_code=400, detail="No valid requests provided")
        
        results = await streaming_service.batch_stream_urls(valid_requests)
        
        return {
            "batch_results": results,
            "processed_at": time.time(),
            "total_requests": len(requests),
            "valid_requests": len(valid_requests)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch stream error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch requests")


@router.get("/embed/{platform}/{video_id}", responses={
    200: {"description": "Embeddable video player", "content": {"text/html": {}}}
})
async def get_embeddable_player(
    platform: str,
    video_id: str,
    quality: str = Query(default="best", description="Video quality"),
    width: int = Query(default=640, description="Player width"),
    height: int = Query(default=360, description="Player height"),
    autoplay: bool = Query(default=False, description="Auto-play video"),
    controls: bool = Query(default=True, description="Show video controls")
):
    """Get embeddable HTML5 video player."""
    try:
        stream_data = await streaming_service.get_stream_url(platform, video_id, quality)
        video_info = stream_data.get("video_info", {})
        
        # Simple HTML5 video player
        autoplay_attr = "autoplay" if autoplay else ""
        controls_attr = "controls" if controls else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{video_info.get('title', 'Video Player')}</title>
            <style>
                body {{ margin: 0; padding: 0; background: #000; }}
                video {{ width: 100%; height: 100%; }}
            </style>
        </head>
        <body>
            <video width="{width}" height="{height}" {controls_attr} {autoplay_attr}>
                <source src="{stream_data['stream_url']}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </body>
        </html>
        """
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": f"public, max-age={settings.stream_cache_ttl}",
                "X-Frame-Options": "SAMEORIGIN"
            }
        )
        
    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Embed player error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create embed player")


# URL-based streaming (convenience endpoints)
@router.get("/url", responses={
    302: {"description": "Stream from any supported URL"},
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def stream_from_url(
    url: str = Query(description="Video URL from any supported platform"),
    quality: str = Query(default="best", description="Video quality"),
    proxy: bool = Query(default=False, description="Proxy through server")
):
    """Stream video from any supported URL (auto-detect platform)."""
    try:
        # Auto-detect platform and video ID from URL
        platform, video_id = _extract_platform_and_id(url)
        
        if proxy:
            # Redirect to proxy endpoint
            return RedirectResponse(
                url=f"/api/v2/stream/proxy/{platform}/{video_id}?quality={quality}",
                status_code=302
            )
        else:
            # Redirect to direct endpoint
            return RedirectResponse(
                url=f"/api/v2/stream/direct/{platform}/{video_id}?quality={quality}",
                status_code=302
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"URL stream error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process URL")


@router.get("/cache/stats", responses={
    200: {"description": "Cache statistics"}
})
async def get_cache_statistics():
    """Get streaming cache statistics."""
    try:
        stats = await streaming_service.get_cache_stats()
        return {
            "cache_stats": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"error": str(e), "timestamp": time.time()}


def _extract_platform_and_id(url: str) -> tuple[str, str]:
    """Extract platform and video ID from URL."""
    import re
    
    # YouTube patterns
    youtube_patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)',
        r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
    ]
    
    # BiliBili patterns
    bilibili_patterns = [
        r'bilibili\.com/video/([a-zA-Z0-9]+)',
        r'b23\.tv/([a-zA-Z0-9]+)'
    ]
    
    # Twitch patterns
    twitch_patterns = [
        r'twitch\.tv/videos/(\d+)',
        r'clips\.twitch\.tv/([a-zA-Z0-9]+)'
    ]
    
    # Instagram patterns
    instagram_patterns = [
        r'instagram\.com/p/([a-zA-Z0-9_-]+)',
        r'instagram\.com/reel/([a-zA-Z0-9_-]+)'
    ]
    
    # Twitter patterns
    twitter_patterns = [
        r'twitter\.com/\w+/status/(\d+)',
        r'x\.com/\w+/status/(\d+)'
    ]
    
    # Check patterns
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            return "youtube", match.group(1)
    
    for pattern in bilibili_patterns:
        match = re.search(pattern, url)
        if match:
            return "bilibili", match.group(1)
    
    for pattern in twitch_patterns:
        match = re.search(pattern, url)
        if match:
            return "twitch", match.group(1)
    
    for pattern in instagram_patterns:
        match = re.search(pattern, url)
        if match:
            return "instagram", match.group(1)
    
    for pattern in twitter_patterns:
        match = re.search(pattern, url)
        if match:
            return "twitter", match.group(1)
    
    raise ValueError(f"Unsupported URL format: {url}")
