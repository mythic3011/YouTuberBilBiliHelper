"""VRChat-specific API routes optimized for VRChat video players."""

import logging
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import quote

from app.services.core.video_service import video_service
from app.services.streaming import StreamingService
from app.exceptions import UnsupportedURLError, VideoNotFoundError
from app.models import ErrorResponse

logger = logging.getLogger(__name__)

# VRChat-specific router
router = APIRouter(prefix="/api/vrchat", tags=["VRChat Optimized"])

# Initialize services
streaming_service = StreamingService()

def extract_video_id_from_url(url: str) -> tuple[str, str]:
    """Extract platform and video ID from any supported URL."""
    from app.routes.simple import extract_video_id_from_url as simple_extract
    return simple_extract(url)


@router.get("/stream", responses={
    200: {"description": "VRChat-optimized stream URL"},
    302: {"description": "Redirect to optimized stream"},
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def vrchat_stream(
    url: str = Query(..., description="Video URL from any supported platform"),
    quality: Literal["720p", "480p", "360p", "best"] = Query("720p", description="Video quality (VRChat-optimized)"),
    player: Literal["avpro", "unity", "auto"] = Query("auto", description="Unity player type optimization"),
    format: Literal["redirect", "proxy", "json"] = Query("redirect", description="Response format")
):
    """
    🎮 **VRChat Stream Endpoint** - GET-only for VRChat compatibility
    
    **VRChat Video Player Requirements:**
    - Only supports GET requests (no POST)
    - Requires direct stream URLs or redirects
    - Works best with MP4 format and moderate quality
    
    **Usage:**
    ```
    GET /api/vrchat/stream?url=https://youtube.com/watch?v=VIDEO_ID
    GET /api/vrchat/stream?url=https://youtu.be/VIDEO_ID&quality=480p&player=avpro
    ```
    
    **VRChat & Unity Optimizations:**
    - MP4 format prioritization for maximum compatibility
    - Quality limited to 720p max for performance
    - Enhanced error handling for VRChat-specific issues
    - Filename sanitization (removes apostrophes and special chars)
    - Unity player-specific codec optimization
    
    **Quality Options:**
    - `720p` - Best quality for short videos
    - `480p` - Recommended for medium videos
    - `360p` - Best for long videos or low bandwidth
    - `best` - Automatic quality selection (limited to 720p)
    
    **Player Options:**
    - `avpro` - AVPro Video optimized (H.264 baseline, AAC audio)
    - `unity` - Unity Video Player optimized (broader codec support)
    - `auto` - Automatic detection based on format availability
    
    **Format Options:**
    - `redirect` - Direct redirect to stream URL (default, VRChat compatible)
    - `proxy` - Stream through our proxy (CORS-friendly)
    - `json` - Return stream URL as JSON (for API integration)
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # VRChat-optimized quality mapping with Unity player considerations
        if player == "avpro":
            # AVPro Video optimized formats (H.264 baseline profile preferred)
            quality_map = {
                "720p": "best[height<=720][ext=mp4][vcodec^=avc1]/best[height<=720][ext=mp4][vcodec*=h264]/best[ext=mp4]",
                "480p": "best[height<=480][ext=mp4][vcodec^=avc1]/best[height<=480][ext=mp4][vcodec*=h264]/best[ext=mp4]", 
                "360p": "best[height<=360][ext=mp4][vcodec^=avc1]/best[height<=360][ext=mp4][vcodec*=h264]/best[ext=mp4]",
                "best": "best[height<=720][ext=mp4][vcodec^=avc1]/best[height<=720][ext=mp4][vcodec*=h264]/best[ext=mp4]"
            }
        elif player == "unity":
            # Unity Video Player optimized (broader codec support)
            quality_map = {
                "720p": "best[height<=720][ext=mp4]/best[height<=720][ext=webm]/best[height<=720]",
                "480p": "best[height<=480][ext=mp4]/best[height<=480][ext=webm]/best[height<=480]", 
                "360p": "best[height<=360][ext=mp4]/best[height<=360][ext=webm]/best[height<=360]",
                "best": "best[height<=720][ext=mp4]/best[height<=720][ext=webm]/best[ext=mp4]"
            }
        else:  # auto
            # Auto-detect best format for VRChat (prioritize MP4)
            quality_map = {
                "720p": "best[height<=720][ext=mp4]/best[height<=720][ext=webm]/best[ext=mp4]",
                "480p": "best[height<=480][ext=mp4]/best[height<=480][ext=webm]/best[ext=mp4]", 
                "360p": "best[height<=360][ext=mp4]/best[height<=360][ext=webm]/best[ext=mp4]",
                "best": "best[height<=720][ext=mp4]/best[height<=720][ext=webm]/best[ext=mp4]"
            }
        
        yt_dlp_quality = quality_map.get(quality, quality_map["720p"])
        
        # Get stream URL using VRChat-optimized quality
        stream_data = await streaming_service.get_stream_url(platform, video_id, yt_dlp_quality)
        stream_url = stream_data["stream_url"]
        
        if format == "json":
            return {
                "platform": platform,
                "video_id": video_id,
                "stream_url": stream_url,
                "quality": quality,
                "player_type": player,
                "vrchat_optimized": True,
                "unity_optimized": True,
                "success": True,
                "notes": f"Stream optimized for VRChat and Unity {player.upper()} player compatibility",
                "codec_info": {
                    "avpro_compatible": player in ["avpro", "auto"],
                    "unity_compatible": player in ["unity", "auto"],
                    "recommended_codecs": "H.264 baseline profile, AAC audio" if player == "avpro" else "H.264/H.265, AAC/MP3 audio"
                }
            }
        elif format == "proxy":
            # Redirect to proxy endpoint with VRChat optimization
            proxy_url = f"/api/v2/stream/proxy/{platform}/{video_id}?quality={quality}&player={player}"
            return RedirectResponse(url=proxy_url, status_code=302)
        else:  # redirect (default - best for VRChat)
            return RedirectResponse(url=stream_url, status_code=302)
            
    except Exception as e:
        error_msg = str(e).lower()
        if "failed to configure url resolver" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail="VRChat URL resolver failed. Check if antivirus is blocking yt-dlp.exe and add an exclusion."
            )
        elif "apostrophe" in error_msg or "'" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="File path contains apostrophes which break VRChat's yt-dlp. Please check your file paths."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Error processing URL for VRChat: {str(e)}")


@router.get("/download", responses={
    302: {"description": "Redirect to VRChat-optimized download"},
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def vrchat_download(
    url: str = Query(..., description="Video URL from any supported platform"),
    quality: Literal["720p", "480p", "360p", "best"] = Query("720p", description="Video quality (VRChat-optimized)"),
    player: Literal["avpro", "unity", "auto"] = Query("auto", description="Unity player type optimization"),
    filename: Optional[str] = Query(None, description="Custom filename (optional)")
):
    """
    💾 **VRChat Download Endpoint** - GET-only for VRChat compatibility
    
    **VRChat Video Player Requirements:**
    - Only supports GET requests (no POST)
    - Requires proper filename encoding for Unicode characters
    - Works best with sanitized filenames (no apostrophes/special chars)
    
    **Usage:**
    ```
    GET /api/vrchat/download?url=https://youtube.com/watch?v=VIDEO_ID
    GET /api/vrchat/download?url=https://youtu.be/VIDEO_ID&quality=480p&player=avpro
    GET /api/vrchat/download?url=https://youtu.be/VIDEO_ID&filename=my_video.mp4
    ```
    
    **VRChat & Unity Optimizations:**
    - Safe filename sanitization (removes apostrophes and special chars)
    - MP4 format enforcement for maximum compatibility
    - Unicode filename support with proper HTTP header encoding
    - Quality optimization based on Unity player type
    - Enhanced error messages for VRChat-specific issues
    
    **Returns:** Redirect to streaming proxy with download headers
    """
    try:
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
        
        # Ensure filename is VRChat-compatible
        filename = video_service._sanitize_filename_for_vrchat(filename)
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        
        # URL-encode filename for safe parameter passing
        encoded_filename = quote(filename.encode('utf-8'))
        
        # Redirect to streaming proxy with VRChat-optimized download headers
        proxy_url = f"/api/v2/stream/proxy/{platform}/{video_id}"
        params = f"?quality={quality}&download=true&filename={encoded_filename}&player={player}"
        
        return RedirectResponse(url=proxy_url + params, status_code=302)
        
    except UnsupportedURLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing VRChat download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process VRChat download: {str(e)}")


@router.get("/info", responses={
    200: {"description": "VRChat compatibility analysis"},
    400: {"model": ErrorResponse, "description": "Invalid URL"},
    404: {"model": ErrorResponse, "description": "Video not found"}
})
async def vrchat_info(
    url: str = Query(..., description="Video URL from any supported platform"),
    player: Literal["avpro", "unity", "auto"] = Query("auto", description="Unity player type for compatibility check")
):
    """
    📋 **VRChat Info Endpoint** - Video compatibility analysis for VRChat
    
    **Usage:**
    ```
    GET /api/vrchat/info?url=https://youtube.com/watch?v=VIDEO_ID
    GET /api/vrchat/info?url=https://youtube.com/watch?v=VIDEO_ID&player=avpro
    ```
    
    **Returns:** Comprehensive VRChat and Unity player compatibility analysis including:
    - Video duration warnings and performance recommendations
    - Character validation in titles and filenames
    - Player-specific codec recommendations
    - Quality suggestions based on player type and video length
    - Memory usage warnings for long videos
    """
    try:
        platform, video_id = extract_video_id_from_url(url)
        
        # Get video info using the video service
        video_info = await video_service.get_video_info(url)
        
        # VRChat and Unity player compatibility checks
        vrchat_compatible = True
        unity_compatible = True
        compatibility_notes = []
        performance_notes = []
        
        # Check duration (VRChat and Unity may have limits)
        if video_info.duration and video_info.duration > 1800:  # 30 minutes
            compatibility_notes.append("Video is longer than 30 minutes - may cause performance issues in VRChat")
            if player == "avpro":
                performance_notes.append("Long videos may consume more memory with AVPro Video")
        
        # Check title for problematic characters
        if video_info.title and ("'" in video_info.title or '"' in video_info.title):
            compatibility_notes.append("Title contains apostrophes/quotes - filename will be sanitized")
        
        # Unity player-specific compatibility
        if player == "avpro":
            performance_notes.append("AVPro Video: Best with H.264 baseline profile and AAC audio")
            performance_notes.append("AVPro Video: Supports hardware decoding on most platforms")
            if video_info.duration and video_info.duration > 3600:  # 1 hour
                compatibility_notes.append("Very long videos may cause memory issues with AVPro Video")
        elif player == "unity":
            performance_notes.append("Unity Video Player: Broader codec support but may use more CPU")
            performance_notes.append("Unity Video Player: Good for various formats including WebM")
        
        # Quality recommendations based on player type and duration
        if video_info.duration:
            if video_info.duration <= 300:  # 5 minutes
                recommended_quality = "720p"
            elif video_info.duration <= 900:  # 15 minutes
                recommended_quality = "480p" if player == "avpro" else "720p"
            else:
                recommended_quality = "360p" if player == "avpro" else "480p"
        else:
            recommended_quality = "720p" if player != "avpro" else "480p"
        
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
            "vrchat_compatible": vrchat_compatible,
            "unity_compatible": unity_compatible,
            "player_type": player,
            "compatibility_notes": compatibility_notes,
            "performance_notes": performance_notes,
            "recommended_quality": recommended_quality,
            "codec_recommendations": {
                "avpro_best": "H.264 baseline profile, AAC audio, MP4 container",
                "unity_best": "H.264/H.265 video, AAC/MP3 audio, MP4/WebM container",
                "current_selection": f"Optimized for {player.upper()} player"
            },
            "vrchat_endpoints": {
                "stream": f"/api/vrchat/stream?url={quote(url)}&player={player}&quality={recommended_quality}",
                "download": f"/api/vrchat/download?url={quote(url)}&player={player}&quality={recommended_quality}",
                "info": f"/api/vrchat/info?url={quote(url)}&player={player}"
            },
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting VRChat video info: {str(e)}")


@router.get("/health", responses={
    200: {"description": "VRChat service health status"}
})
async def vrchat_health():
    """
    ❤️ **VRChat Health Check** - Check VRChat-specific service status
    
    **Usage:** `GET /api/vrchat/health`
    
    **Returns:** Health status for VRChat-optimized services
    """
    return {
        "status": "healthy",
        "service": "VRChat Video API",
        "version": "2.0.0",
        "features": {
            "get_only_endpoints": True,
            "unicode_filename_support": True,
            "unity_player_optimization": True,
            "avpro_video_support": True,
            "filename_sanitization": True,
            "error_handling_enhanced": True
        },
        "endpoints": {
            "stream": "/api/vrchat/stream - VRChat-optimized streaming",
            "download": "/api/vrchat/download - VRChat-optimized downloads", 
            "info": "/api/vrchat/info - Compatibility analysis",
            "health": "/api/vrchat/health - This endpoint"
        },
        "supported_players": ["avpro", "unity", "auto"],
        "supported_qualities": ["720p", "480p", "360p", "best"],
        "notes": "All endpoints use GET method for VRChat compatibility"
    }
