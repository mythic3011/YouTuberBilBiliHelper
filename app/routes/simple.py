"""Simple, user-friendly API endpoints."""

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional, Literal
from urllib.parse import urlparse, parse_qs
import re

from app.services.video_service import VideoService
from app.services.streaming_service import StreamingService
from app.exceptions import UnsupportedURLError, VideoNotFoundError
from app.models import VideoQuality
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Simple API"])

# Initialize services
video_service = VideoService()
streaming_service = StreamingService()

def extract_video_id_from_url(url: str) -> tuple[str, str]:
    """Extract platform and video ID from any supported URL."""
    # YouTube patterns
    if 'youtube.com' in url or 'youtu.be' in url:
        if 'youtu.be' in url:
            video_id = url.split('/')[-1].split('?')[0]
        else:
            parsed = urlparse(url)
            if 'watch' in parsed.path:
                query_params = parse_qs(parsed.query)
                video_id = query_params.get('v', [''])[0]
            else:
                video_id = parsed.path.split('/')[-1]
        return 'youtube', video_id
    
    # BiliBili patterns
    elif 'bilibili.com' in url:
        if 'BV' in url:
            match = re.search(r'BV[A-Za-z0-9]+', url)
            video_id = match.group(0) if match else ''
        else:
            video_id = url.split('/')[-1].split('?')[0]
        return 'bilibili', video_id
    
    # Twitch patterns
    elif 'twitch.tv' in url:
        if 'clips.twitch.tv' in url:
            video_id = url.split('/')[-1]
            return 'twitch', video_id
        elif '/videos/' in url:
            video_id = url.split('/videos/')[-1].split('?')[0]
            return 'twitch', video_id
        else:
            video_id = url.split('/')[-1]
            return 'twitch', video_id
    
    # Instagram patterns
    elif 'instagram.com' in url:
        if '/p/' in url:
            video_id = url.split('/p/')[-1].split('/')[0]
        elif '/reel/' in url:
            video_id = url.split('/reel/')[-1].split('/')[0]
        else:
            video_id = url.split('/')[-1].split('?')[0]
        return 'instagram', video_id
    
    # Twitter patterns
    elif 'twitter.com' in url or 'x.com' in url:
        if '/status/' in url:
            video_id = url.split('/status/')[-1].split('?')[0]
        else:
            video_id = url.split('/')[-1].split('?')[0]
        return 'twitter', video_id
    
    else:
        raise UnsupportedURLError("URL format not supported")

@router.get("/stream")
async def get_stream_simple(
    url: str = Query(..., description="Video URL from any supported platform"),
    quality: Literal["highest", "lowest", "720p", "480p", "360p"] = Query("highest", description="Video quality"),
    format: Literal["redirect", "proxy", "json"] = Query("redirect", description="Response format")
):
    """
    🎬 **Simple Stream Endpoint** - Get video stream from any URL
    
    **Usage:**
    - `GET /api/stream?url=https://youtube.com/watch?v=VIDEO_ID`
    - `GET /api/stream?url=https://youtu.be/VIDEO_ID&quality=720p`
    - `GET /api/stream?url=https://twitch.tv/videos/123456&format=json`
    
    **Supported Platforms:** YouTube, BiliBili, Twitch, Instagram, Twitter
    
    **Quality Options:** highest, lowest, 720p, 480p, 360p
    
    **Format Options:**
    - `redirect` (default): Direct redirect to video stream
    - `proxy`: Stream through our proxy (CORS-friendly)  
    - `json`: Return stream URL as JSON
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # Map simple quality names to yt-dlp quality strings
        quality_map = {
            "highest": "best",
            "lowest": "worst", 
            "720p": "720p",
            "480p": "480p",
            "360p": "360p"
        }
        yt_dlp_quality = quality_map.get(quality, "best")
        
        # Get stream URL using quality string
        stream_data = await streaming_service.get_stream_url(platform, video_id, yt_dlp_quality)
        stream_url = stream_data["stream_url"]
        
        if format == "json":
            return {
                "platform": platform,
                "video_id": video_id,
                "stream_url": stream_url,
                "quality": quality,
                "success": True
            }
        elif format == "proxy":
            return RedirectResponse(
                url=f"/api/v2/stream/proxy/{platform}/{video_id}?quality={quality}",
                status_code=302
            )
        else:  # redirect
            return RedirectResponse(url=stream_url, status_code=302)
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing URL: {str(e)}")

@router.get("/info")
async def get_video_info_simple(
    url: str = Query(..., description="Video URL from any supported platform")
):
    """
    📋 **Simple Info Endpoint** - Get video information from any URL
    
    **Usage:**
    - `GET /api/info?url=https://youtube.com/watch?v=VIDEO_ID`
    - `GET /api/info?url=https://youtu.be/VIDEO_ID`
    
    **Returns:** Video title, duration, uploader, thumbnail, etc.
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # Get video info using the video service with the original URL
        video_info = await video_service.get_video_info(url)
        
        # Also try to get stream URL to check availability
        try:
            stream_data = await streaming_service.get_stream_url(platform, video_id)
            stream_available = True
        except Exception as e:
            logger.debug(f"Stream not available for {platform}:{video_id}: {e}")
            stream_available = False
        
        return {
            "platform": platform,
            "video_id": video_id,
            "info": {
                "id": video_info.id,
                "title": video_info.title,
                "description": video_info.description,
                "duration": video_info.duration,
                "uploader": video_info.uploader,
                "upload_date": video_info.upload_date,
                "view_count": video_info.view_count,
                "like_count": video_info.like_count,
                "thumbnail": video_info.thumbnail
            },
            "stream_available": stream_available,
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting video info: {str(e)}")

@router.get("/download")
async def get_download_simple(
    url: str = Query(..., description="Video URL from any supported platform"),
    quality: Literal["highest", "lowest", "720p", "480p", "360p"] = Query("highest", description="Video quality"),
    filename: Optional[str] = Query(None, description="Custom filename (optional)")
):
    """
    💾 **Simple Download Endpoint** - Download video from any URL
    
    **Usage:**
    - `GET /api/download?url=https://youtube.com/watch?v=VIDEO_ID`
    - `GET /api/download?url=https://youtu.be/VIDEO_ID&quality=720p`
    - `GET /api/download?url=https://youtu.be/VIDEO_ID&filename=my_video.mp4`
    
    **Note:** This streams the video through our proxy with download headers
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # Get video info for filename if not provided
        if not filename:
            try:
                video_info = await video_service.get_video_info(url)
                title = video_info.title or f"{platform}_{video_id}"
                # Clean filename
                import re
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                safe_title = re.sub(r'[-\s]+', '_', safe_title)
                filename = f"{safe_title}.mp4"
            except Exception as e:
                logger.debug(f"Could not get video info for filename: {e}")
                filename = f"{platform}_{video_id}.mp4"
        
        # Redirect to proxy with download headers
        return RedirectResponse(
            url=f"/api/v2/stream/proxy/{platform}/{video_id}?quality={quality}&download=true&filename={filename}",
            status_code=302
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing download: {str(e)}")

@router.get("/formats")
async def get_available_formats_simple(
    url: str = Query(..., description="Video URL from any supported platform")
):
    """
    🎯 **Simple Formats Endpoint** - Get available quality formats for any URL
    
    **Usage:**
    - `GET /api/formats?url=https://youtube.com/watch?v=VIDEO_ID`
    
    **Returns:** Available quality options and format details
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # Get video info
        video_info = await video_service.get_video_info(url)
        
        # Extract available qualities (this is a simplified version)
        available_qualities = ["highest", "lowest", "720p", "480p", "360p"]
        
        return {
            "platform": platform,
            "video_id": video_id,
            "available_qualities": available_qualities,
            "recommended_quality": "highest",
            "video_info": {
                "id": video_info.id,
                "title": video_info.title,
                "description": video_info.description,
                "duration": video_info.duration,
                "uploader": video_info.uploader,
                "upload_date": video_info.upload_date,
                "view_count": video_info.view_count,
                "like_count": video_info.like_count,
                "thumbnail": video_info.thumbnail
            },
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting formats: {str(e)}")

@router.get("/embed")
async def get_embed_simple(
    url: str = Query(..., description="Video URL from any supported platform"),
    width: int = Query(640, description="Player width"),
    height: int = Query(360, description="Player height"),
    quality: Literal["highest", "lowest", "720p", "480p", "360p"] = Query("highest", description="Video quality")
):
    """
    📺 **Simple Embed Endpoint** - Get embeddable HTML5 video player
    
    **Usage:**
    - `GET /api/embed?url=https://youtube.com/watch?v=VIDEO_ID`
    - `GET /api/embed?url=https://youtu.be/VIDEO_ID&width=800&height=450`
    
    **Returns:** HTML5 video player ready for embedding
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # Redirect to the existing embed endpoint
        return RedirectResponse(
            url=f"/api/v2/stream/embed/{platform}/{video_id}?width={width}&height={height}&quality={quality}",
            status_code=302
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating embed: {str(e)}")

@router.get("/platforms")
async def get_supported_platforms():
    """
    🌐 **Supported Platforms** - List all supported video platforms
    
    **Usage:** `GET /api/platforms`
    
    **Returns:** List of supported platforms with example URLs
    """
    return {
        "supported_platforms": [
            {
                "name": "YouTube",
                "platform_id": "youtube", 
                "domains": ["youtube.com", "youtu.be"],
                "example_urls": [
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://youtu.be/dQw4w9WgXcQ"
                ],
                "features": ["streaming", "download", "info", "embed", "all_qualities"]
            },
            {
                "name": "BiliBili",
                "platform_id": "bilibili",
                "domains": ["bilibili.com"],
                "example_urls": [
                    "https://www.bilibili.com/video/BV1xx411c7mu"
                ],
                "features": ["streaming", "download", "info", "embed"],
                "notes": "May require authentication for some videos"
            },
            {
                "name": "Twitch",
                "platform_id": "twitch", 
                "domains": ["twitch.tv", "clips.twitch.tv"],
                "example_urls": [
                    "https://clips.twitch.tv/PowerfulCalmSalmonTF2John",
                    "https://www.twitch.tv/videos/123456789"
                ],
                "features": ["streaming", "download", "info", "embed"],
                "notes": "Works with clips and VODs"
            },
            {
                "name": "Instagram", 
                "platform_id": "instagram",
                "domains": ["instagram.com"],
                "example_urls": [
                    "https://www.instagram.com/p/ABC123/",
                    "https://www.instagram.com/reel/ABC123/"
                ],
                "features": ["streaming", "download", "info"],
                "notes": "May require authentication for private posts"
            },
            {
                "name": "Twitter/X",
                "platform_id": "twitter", 
                "domains": ["twitter.com", "x.com"],
                "example_urls": [
                    "https://twitter.com/user/status/1234567890",
                    "https://x.com/user/status/1234567890"
                ],
                "features": ["streaming", "download", "info"],
                "notes": "May require authentication for some videos"
            }
        ],
        "total_platforms": 5,
        "simple_endpoints": [
            "/api/stream - Get video stream",
            "/api/info - Get video information", 
            "/api/download - Download video",
            "/api/formats - Get available formats",
            "/api/embed - Get embeddable player",
            "/api/platforms - This endpoint"
        ]
    }

@router.get("/health")
async def health_check_simple():
    """
    ✅ **Simple Health Check** - Check if the API is working
    
    **Usage:** `GET /api/health`
    
    **Returns:** Simple health status
    """
    return RedirectResponse(url="/api/v2/system/health", status_code=302)
