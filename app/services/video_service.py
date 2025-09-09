"""Video processing service using yt-dlp."""

import asyncio
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import yt_dlp
from app.config import settings
from app.models import VideoInfo, VideoQuality, VideoFormat, TaskStatus, TaskInfo
from app.exceptions import (
    VideoNotFoundError, DownloadError, UnsupportedURLError, ValidationError
)
from app.services.storage_service import storage_service
from app.services.redis_service import redis_service
from app.services.auth_service import auth_service
import logging

logger = logging.getLogger(__name__)


class VideoService:
    """Service for video processing and downloading."""
    
    def __init__(self):
        self._download_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        self._active_downloads: Dict[str, asyncio.Task] = {}
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is from YouTube."""
        parsed = urlparse(url)
        return parsed.netloc in [
            "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"
        ]
    
    def _is_bilibili_url(self, url: str) -> bool:
        """Check if URL is from BiliBili."""
        parsed = urlparse(url)
        return parsed.netloc in [
            "www.bilibili.com", "bilibili.com", "b23.tv"
        ]
    
    def _is_twitch_url(self, url: str) -> bool:
        """Check if URL is from Twitch."""
        parsed = urlparse(url)
        return parsed.netloc in [
            "www.twitch.tv", "twitch.tv", "clips.twitch.tv"
        ]
    
    def _is_instagram_url(self, url: str) -> bool:
        """Check if URL is from Instagram."""
        parsed = urlparse(url)
        return parsed.netloc in [
            "www.instagram.com", "instagram.com"
        ]
    
    def _is_twitter_url(self, url: str) -> bool:
        """Check if URL is from Twitter/X."""
        parsed = urlparse(url)
        return parsed.netloc in [
            "twitter.com", "www.twitter.com", "x.com", "www.x.com"
        ]
    
    def _validate_url(self, url: str) -> str:
        """Validate and determine platform for URL."""
        if self._is_youtube_url(url):
            return "youtube"
        elif self._is_bilibili_url(url):
            return "bilibili"
        elif self._is_twitch_url(url):
            return "twitch"
        elif self._is_instagram_url(url):
            return "instagram"
        elif self._is_twitter_url(url):
            return "twitter"
        else:
            raise UnsupportedURLError(
                "URL not supported",
                code="UNSUPPORTED_URL",
                detail="Supported platforms: YouTube, BiliBili, Twitch, Instagram, Twitter"
            )
    
    async def get_video_info(self, url: str) -> VideoInfo:
        """Extract video information without downloading."""
        try:
            platform = self._validate_url(url)
            
            # Check cache first (skip if Redis unavailable)
            cache_key = f"video_info:{url}"
            try:
                cached_info = await redis_service.get_json(cache_key)
                if cached_info:
                    return VideoInfo(**cached_info)
            except Exception:
                # Continue without cache if Redis unavailable
                pass
            
            # Base yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': False,
            }
            
            # Add authentication options if available
            platform = self._validate_url(url)
            auth_opts = auth_service.get_yt_dlp_options(platform)
            ydl_opts.update(auth_opts)
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            info_dict = await loop.run_in_executor(
                None, self._extract_info, url, ydl_opts
            )
            
            if not info_dict:
                raise VideoNotFoundError(
                    "Video not found or unavailable",
                    code="VIDEO_NOT_FOUND"
                )
            
            # Convert to our model
            video_info = VideoInfo(
                id=info_dict.get('id', ''),
                title=info_dict.get('title', 'Unknown'),
                description=info_dict.get('description'),
                duration=info_dict.get('duration'),
                uploader=info_dict.get('uploader'),
                upload_date=info_dict.get('upload_date'),
                view_count=info_dict.get('view_count'),
                like_count=info_dict.get('like_count'),
                thumbnail=info_dict.get('thumbnail'),
                formats=info_dict.get('formats', [])
            )
            
            # Cache for 1 hour (skip if Redis unavailable)
            try:
                await redis_service.set_json(cache_key, video_info.dict(), ttl=3600)
            except Exception:
                # Continue without cache if Redis unavailable
                pass
            
            return video_info
            
        except Exception as e:
            if isinstance(e, (UnsupportedURLError, VideoNotFoundError)):
                raise
            logger.error(f"Error extracting video info: {e}")
            raise VideoNotFoundError(
                "Failed to extract video information",
                code="EXTRACTION_ERROR",
                detail=str(e)
            )
    
    def _extract_info(self, url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract info using yt-dlp (runs in executor)."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"yt-dlp extraction error: {e}")
            return None
    
    def _get_format_selector(self, quality: VideoQuality) -> str:
        """Get yt-dlp format selector based on quality."""
        if quality == VideoQuality.HIGHEST:
            return "best"
        elif quality == VideoQuality.LOWEST:
            return "worst"
        elif quality == VideoQuality.BEST_AUDIO:
            return "bestaudio"
        elif quality == VideoQuality.BEST_VIDEO:
            return "bestvideo"
        else:
            return "best[height<=720]"  # Default to 720p or lower
    
    async def start_download(
        self,
        url: str,
        quality: VideoQuality = VideoQuality.HIGHEST,
        format_type: VideoFormat = VideoFormat.MP4,
        audio_only: bool = False,
        custom_filename: Optional[str] = None
    ) -> str:
        """Start video download and return task ID."""
        
        platform = self._validate_url(url)
        task_id = str(uuid.uuid4())
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            updated_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            message="Download queued"
        )
        
        # Store task info in Redis
        await redis_service.set_json(f"task:{task_id}", task_info.dict(), ttl=86400)  # 24 hours
        
        # Start download task
        download_task = asyncio.create_task(
            self._download_video(
                task_id, url, platform, quality, format_type, audio_only, custom_filename
            )
        )
        self._active_downloads[task_id] = download_task
        
        return task_id
    
    async def _download_video(
        self,
        task_id: str,
        url: str,
        platform: str,
        quality: VideoQuality,
        format_type: VideoFormat,
        audio_only: bool,
        custom_filename: Optional[str]
    ) -> None:
        """Download video (background task)."""
        
        async with self._download_semaphore:
            try:
                # Update task status
                await self._update_task_status(
                    task_id, TaskStatus.PROCESSING, "Starting download..."
                )
                
                # Get video info
                video_info = await self.get_video_info(url)
                
                # Check duration limit
                if video_info.duration and video_info.duration > settings.max_video_duration_minutes * 60:
                    raise ValidationError(
                        f"Video too long (max {settings.max_video_duration_minutes} minutes)",
                        code="VIDEO_TOO_LONG"
                    )
                
                # Update task with video info
                await self._update_task_info(task_id, video_info=video_info)
                
                # Ensure storage is available
                await storage_service.ensure_storage_available()
                
                # Prepare download options
                filename = custom_filename or f"{video_info.id}.%(ext)s"
                output_path = storage_service.get_file_path(platform, filename)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                ydl_opts = self._build_ydl_options(
                    str(output_path.parent / filename),
                    quality,
                    format_type,
                    audio_only
                )
                
                # Progress hook
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        percent = d.get('_percent_str', '0%').strip('%')
                        try:
                            progress = float(percent) / 100
                            asyncio.create_task(
                                self._update_task_progress(task_id, progress, f"Downloading... {percent}%")
                            )
                        except (ValueError, TypeError):
                            pass
                
                ydl_opts['progress_hooks'] = [progress_hook]
                
                # Download video
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self._download_with_ydl, url, ydl_opts
                )
                
                # Find downloaded file
                downloaded_file = None
                for file_path in output_path.parent.glob(f"{video_info.id}.*"):
                    if file_path.is_file():
                        downloaded_file = file_path
                        break
                
                if not downloaded_file or not downloaded_file.exists():
                    raise DownloadError("Download completed but file not found")
                
                # Update task as completed
                file_info = await storage_service.get_file_info(downloaded_file)
                await self._update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    "Download completed successfully",
                    download_url=f"/api/v2/files/{downloaded_file.name}",
                    file_size=file_info['size'] if file_info else None
                )
                
            except Exception as e:
                logger.error(f"Download failed for task {task_id}: {e}")
                await self._update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    "Download failed",
                    error=str(e)
                )
            finally:
                # Clean up
                if task_id in self._active_downloads:
                    del self._active_downloads[task_id]
    
    def _build_ydl_options(
        self,
        output_template: str,
        quality: VideoQuality,
        format_type: VideoFormat,
        audio_only: bool
    ) -> Dict[str, Any]:
        """Build yt-dlp options based on parameters."""
        
        opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        if audio_only:
            opts['format'] = 'bestaudio/best'
            if format_type in [VideoFormat.MP3, VideoFormat.M4A]:
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type.value,
                    'preferredquality': '192',
                }]
        else:
            # Video formats
            if quality == VideoQuality.HIGHEST:
                format_selector = f'best[ext={format_type.value}]/best'
            elif quality == VideoQuality.LOWEST:
                format_selector = f'worst[ext={format_type.value}]/worst'
            elif quality == VideoQuality.BEST_VIDEO:
                format_selector = f'bestvideo[ext={format_type.value}]/bestvideo'
            else:
                format_selector = f'best[ext={format_type.value}]/best'
            
            opts['format'] = format_selector
        
        return opts
    
    def _download_with_ydl(self, url: str, ydl_opts: Dict[str, Any]) -> None:
        """Download using yt-dlp (runs in executor)."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    
    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        message: str,
        download_url: Optional[str] = None,
        error: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> None:
        """Update task status in Redis."""
        try:
            task_info = await redis_service.get_json(f"task:{task_id}")
            if task_info:
                task_info['status'] = status.value
                task_info['message'] = message
                task_info['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                if download_url:
                    task_info['download_url'] = download_url
                if error:
                    task_info['error'] = error
                if file_size:
                    task_info['file_size'] = file_size
                
                await redis_service.set_json(f"task:{task_id}", task_info, ttl=86400)
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
    
    async def _update_task_progress(self, task_id: str, progress: float, message: str) -> None:
        """Update task progress."""
        try:
            task_info = await redis_service.get_json(f"task:{task_id}")
            if task_info:
                task_info['progress'] = progress
                task_info['message'] = message
                task_info['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                await redis_service.set_json(f"task:{task_id}", task_info, ttl=86400)
        except Exception as e:
            logger.error(f"Error updating task progress: {e}")
    
    async def _update_task_info(self, task_id: str, video_info: VideoInfo) -> None:
        """Update task with video information."""
        try:
            task_info = await redis_service.get_json(f"task:{task_id}")
            if task_info:
                task_info['video_info'] = video_info.dict()
                await redis_service.set_json(f"task:{task_id}", task_info, ttl=86400)
        except Exception as e:
            logger.error(f"Error updating task info: {e}")
    
    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status from Redis."""
        try:
            task_data = await redis_service.get_json(f"task:{task_id}")
            if task_data:
                return TaskInfo(**task_data)
            return None
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    async def cancel_download(self, task_id: str) -> bool:
        """Cancel active download."""
        try:
            if task_id in self._active_downloads:
                task = self._active_downloads[task_id]
                task.cancel()
                del self._active_downloads[task_id]
                
                # Update task status
                await self._update_task_status(
                    task_id, TaskStatus.FAILED, "Download cancelled"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling download: {e}")
            return False
    
    async def get_stream_url(self, url: str, quality: VideoQuality = VideoQuality.HIGHEST) -> str:
        """Get direct stream URL for video."""
        try:
            platform = self._validate_url(url)
            
            # Select format based on quality
            format_selector = self._get_format_selector(quality)
            
            # Base yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': False,
                'format': format_selector,
            }
            
            # Add authentication options if available
            auth_opts = auth_service.get_yt_dlp_options(platform)
            ydl_opts.update(auth_opts)
            
            # Get video info with formats
            loop = asyncio.get_event_loop()
            info_dict = await loop.run_in_executor(
                None, self._extract_info, url, ydl_opts
            )
            
            if not info_dict:
                raise VideoNotFoundError("Could not extract stream information")
            
            # Get the direct URL from yt-dlp
            stream_url = info_dict.get('url')
            if not stream_url:
                raise VideoNotFoundError("No stream URL available")
            
            return stream_url
            
        except Exception as e:
            if isinstance(e, (UnsupportedURLError, VideoNotFoundError)):
                raise
            logger.error(f"Error getting stream URL: {e}")
            raise VideoNotFoundError(
                "Failed to get stream URL",
                code="STREAM_ERROR",
                detail=str(e)
            )


# Global video service instance
video_service = VideoService()
