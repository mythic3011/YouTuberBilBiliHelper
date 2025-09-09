"""Instagram platform processor for reels and posts."""

from typing import List, Dict, Any
from app.platforms.base import BasePlatformProcessor
from app.models import VideoInfo, VideoFormat, DownloadOptions
from app.exceptions import VideoNotFoundError
import logging

logger = logging.getLogger(__name__)


class InstagramProcessor(BasePlatformProcessor):
    """Instagram platform processor for reels and posts."""
    
    @property
    def platform_name(self) -> str:
        return "instagram"
    
    @property
    def supported_domains(self) -> List[str]:
        return ["instagram.com", "www.instagram.com"]
    
    async def extract_info(self, url: str) -> VideoInfo:
        """Extract Instagram video information."""
        # Instagram extraction would be handled by yt-dlp
        # This is a placeholder for the platform interface
        raise NotImplementedError("Instagram extraction handled by yt-dlp core")
    
    async def get_download_formats(self, url: str) -> List[VideoFormat]:
        """Get available download formats for Instagram video."""
        # Instagram typically provides limited format options
        return [
            VideoFormat(format_id="mp4", ext="mp4", quality="source"),
            VideoFormat(format_id="mp4_720", ext="mp4", quality="720p"),
        ]
    
    async def download(self, url: str, options: DownloadOptions) -> str:
        """Download Instagram video."""
        # Implementation would use yt-dlp for actual downloading
        raise NotImplementedError("Download handled by yt-dlp core")
    
    async def get_stream_url(self, url: str, quality: str = "highest") -> str:
        """Get direct stream URL for Instagram video."""
        # Implementation would use yt-dlp to get stream URLs
        raise NotImplementedError("Stream URL extraction handled by yt-dlp core")
