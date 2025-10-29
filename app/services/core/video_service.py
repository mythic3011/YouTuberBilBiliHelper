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
from app.services.infrastructure.storage_service import storage_service
from app.services.infrastructure.redis_service import redis_service
from app.services.core.auth_service import auth_service
from app.services.download.concurrent_manager import concurrent_download_manager
from app.services.download.bilibili_manager import bilibili_concurrent_manager
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
    
    def _sanitize_filename_for_vrchat(self, filename: str) -> str:
        """Sanitize filename to be VRChat-compatible (no apostrophes, special chars)."""
        import re
        import unicodedata
        
        # Remove apostrophes and other problematic characters for VRChat
        filename = filename.replace("'", "").replace('"', "")
        filename = filename.replace("'", "").replace("'", "")  # Smart quotes
        filename = filename.replace(""", "").replace(""", "")  # Smart double quotes
        
        # Normalize unicode characters (e.g., É → E)
        filename = unicodedata.normalize('NFD', filename)
        filename = ''.join(c for c in filename if unicodedata.category(c) != 'Mn')
        
        # Replace other problematic characters
        filename = re.sub(r'[<>:"|?*]', '', filename)  # Windows forbidden chars
        filename = re.sub(r'[^\w\s\-_\.]', '', filename, flags=re.ASCII)  # Keep only ASCII safe chars
        filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
        filename = re.sub(r'_{2,}', '_', filename)  # Replace multiple underscores
        filename = filename.strip('_')  # Remove leading/trailing underscores
        
        # Ensure filename is not empty
        if not filename:
            filename = "video"
        
        return filename
    
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
            
            # VRChat-compatible base yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': False,
                # VRChat compatibility improvements
                'no_color': True,
                'prefer_ffmpeg': True,
                'merge_output_format': 'mp4',
                'retries': 3,
                'fragment_retries': 3,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
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
        custom_filename: Optional[str] = None,
        user_session: Optional[str] = None
    ) -> str:
        """Start video download with concurrent access management and return task ID."""
        
        platform = self._validate_url(url)
        
        # Generate user session if not provided
        if not user_session:
            user_session = str(uuid.uuid4())
        
        # Check if this is a Bilibili URL and use specialized manager
        if platform == "bilibili":
            logger.info(f"Using Bilibili-specific concurrent manager for {url}")
            job_id = await bilibili_concurrent_manager.handle_bilibili_download(
                url=url,
                quality=quality.value,
                format_type=format_type.value,
                user_session=user_session,
                custom_filename=custom_filename
            )
        else:
            # Use general concurrent download manager for other platforms
            job_id = await concurrent_download_manager.submit_download_job(
                url=url,
                quality=quality.value,
                format_type=format_type.value,
                user_session=user_session,
                custom_filename=custom_filename
            )
        
        # Use job_id as task_id for consistency
        task_id = job_id
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            updated_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            message="Download queued for concurrent processing"
        )
        
        # Store task info in Redis
        await redis_service.set_json(f"task:{task_id}", task_info.dict(), ttl=86400)  # 24 hours
        
        # Start download task with concurrent management
        download_task = asyncio.create_task(
            self._concurrent_download_video(
                task_id, url, platform, quality, format_type, audio_only, custom_filename
            )
        )
        self._active_downloads[task_id] = download_task
        
        return task_id
    
    async def _concurrent_download_video(
        self,
        task_id: str,
        url: str,
        platform: str,
        quality: VideoQuality,
        format_type: VideoFormat,
        audio_only: bool,
        custom_filename: Optional[str]
    ) -> None:
        """Download video with concurrent access management (background task)."""
        
        try:
            # Process through concurrent download manager
            result = await concurrent_download_manager.process_download_job(
                job_id=task_id,
                download_func=self._execute_download,
                platform=platform,
                quality=quality,
                format_type=format_type,
                audio_only=audio_only,
                custom_filename=custom_filename
            )
            
            # Update task status with result
            if result["status"] == "completed":
                await self._update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    f"Download completed: {result['unique_filename']}" + (" (reused existing)" if result.get('reused') else ""),
                    download_url=f"/api/v2/files/{Path(result['file_path']).name}"
                )
            else:
                await self._update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    "Download failed"
                )
                
        except Exception as e:
            logger.error(f"Concurrent download failed for task {task_id}: {e}")
            await self._update_task_status(
                task_id,
                TaskStatus.FAILED,
                f"Download failed: {str(e)}"
            )
        finally:
            # Clean up from active downloads
            if task_id in self._active_downloads:
                del self._active_downloads[task_id]
    
    async def _execute_download(
        self,
        url: str,
        platform: str,
        quality: VideoQuality,
        format_type: VideoFormat,
        audio_only: bool,
        custom_filename: Optional[str],
        output_path: str,
        unique_filename: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the actual download with unique filename."""
        
        # Get video info
        video_info = await self.get_video_info(url)
        
        # Build yt-dlp options with unique output path
        ydl_opts = self._build_ydl_options(
            quality=quality,
            format_type=format_type,
            audio_only=audio_only,
            output_path=output_path,
            unity_player="auto"
        )
        
        # Use unique filename template
        output_dir = Path(output_path).parent
        filename_template = f"{Path(unique_filename).stem}.%(ext)s"
        ydl_opts['outtmpl'] = str(output_dir / filename_template)
        
        # Execute download
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._download_with_ydl, url, ydl_opts
        )
        
        return {
            "success": True,
            "file_path": output_path,
            "unique_filename": unique_filename
        }
    
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
                
                # Prepare VRChat-compatible download options
                if custom_filename:
                    # Sanitize custom filename for VRChat compatibility
                    base_name = Path(custom_filename).stem
                    extension = Path(custom_filename).suffix or ".mp4"
                    safe_name = self._sanitize_filename_for_vrchat(base_name)
                    filename = f"{safe_name}{extension}"
                else:
                    # Create VRChat-compatible filename from video info
                    safe_title = self._sanitize_filename_for_vrchat(video_info.title or video_info.id)
                    filename = f"{safe_title}.%(ext)s"
                
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
        audio_only: bool,
        unity_player: str = "auto"
    ) -> Dict[str, Any]:
        """Build yt-dlp options based on parameters with VRChat compatibility."""
        
        # VRChat-compatible base options
        opts = {
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            # VRChat compatibility fixes
            'writeinfojson': False,  # Avoid extra files
            'writesubtitles': False,  # Avoid subtitle files
            'writeautomaticsub': False,  # Avoid automatic subtitles
            'ignoreerrors': False,  # Don't ignore errors for VRChat compatibility
            'no_color': True,  # Avoid color codes in output
            'extract_flat': False,  # Ensure full extraction
            # Format selection for VRChat compatibility
            'merge_output_format': 'mp4',  # Always merge to MP4 for VRChat
            'prefer_ffmpeg': True,  # Use ffmpeg for better compatibility
            # Network settings for stability
            'retries': 3,  # Retry failed downloads
            'fragment_retries': 3,  # Retry failed fragments
            'socket_timeout': 30,  # Increase timeout
            # User agent for better compatibility
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }
        
        if audio_only:
            # VRChat-compatible audio formats
            opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best'
            if format_type in [VideoFormat.MP3, VideoFormat.M4A]:
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type.value,
                    'preferredquality': '192',
                }]
        else:
            # Unity player-specific video formats
            if unity_player == "avpro":
                # AVPro Video optimized formats (H.264 baseline profile preferred)
                if quality == VideoQuality.HIGHEST:
                    format_selector = 'best[height<=720][ext=mp4][vcodec^=avc1]/best[height<=720][ext=mp4][vcodec*=h264]/best[ext=mp4]'
                elif quality == VideoQuality.LOWEST:
                    format_selector = 'worst[ext=mp4][vcodec^=avc1]/worst[ext=mp4][vcodec*=h264]/worst[ext=mp4]'
                elif quality == VideoQuality.BEST_VIDEO:
                    format_selector = 'bestvideo[height<=720][ext=mp4][vcodec^=avc1]/bestvideo[ext=mp4][vcodec*=h264]/bestvideo[ext=mp4]'
                else:
                    format_selector = 'best[height<=480][ext=mp4][vcodec^=avc1]/best[height<=480][ext=mp4][vcodec*=h264]/best[ext=mp4]'
            elif unity_player == "unity":
                # Unity Video Player optimized (broader codec support)
                if quality == VideoQuality.HIGHEST:
                    format_selector = 'best[ext=mp4]/best[ext=webm]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
                elif quality == VideoQuality.LOWEST:
                    format_selector = 'worst[ext=mp4]/worst[ext=webm]/worstvideo[ext=mp4]+bestaudio[ext=m4a]/worst'
                elif quality == VideoQuality.BEST_VIDEO:
                    format_selector = 'bestvideo[ext=mp4]/bestvideo[ext=webm]/bestvideo'
                else:
                    format_selector = 'best[height<=720][ext=mp4]/best[height<=720][ext=webm]/best[ext=mp4]/best[ext=webm]/best'
            else:
                # Auto/Default VRChat-compatible format with quality limit
                format_selector = 'best[height<=720][ext=mp4]/best[height<=720][ext=webm]/best[ext=mp4]/best[ext=webm]/best'
            
            opts['format'] = format_selector
            
            # Ensure final output is MP4 for VRChat compatibility
            if format_type == VideoFormat.MP4:
                opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
        
        return opts
    
    def _download_with_ydl(self, url: str, ydl_opts: Dict[str, Any]) -> None:
        """Download using yt-dlp with VRChat compatibility (runs in executor)."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            # VRChat-specific error handling
            if "failed to configure url resolver" in error_msg:
                raise DownloadError(
                    "VRChat URL resolver failed. This may be due to antivirus software blocking yt-dlp.exe. "
                    "Please add an exclusion for yt-dlp.exe in your antivirus settings."
                )
            elif "apostrophe" in error_msg or "'" in error_msg:
                raise DownloadError(
                    "File path contains apostrophes which break VRChat's yt-dlp. "
                    "Please ensure your file paths don't contain apostrophes or special characters."
                )
            else:
                raise DownloadError(f"Download failed: {str(e)}")
        except Exception as e:
            raise DownloadError(f"Unexpected download error: {str(e)}")
    
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
            
            # VRChat-compatible base yt-dlp options for streaming
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'extract_flat': False,
                'format': format_selector,
                # VRChat compatibility improvements
                'no_color': True,
                'prefer_ffmpeg': True,
                'retries': 3,
                'fragment_retries': 3,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
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
