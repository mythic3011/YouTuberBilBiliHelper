"""Concurrent download management service for handling multiple users downloading the same video."""

import asyncio
import hashlib
import time
import uuid
import os
from pathlib import Path
from typing import Dict, Optional, Set, Any, List
from dataclasses import dataclass
from app.config import settings
from app.services.infrastructure.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


@dataclass
class DownloadJob:
    """Represents a download job with unique identification."""
    job_id: str
    video_id: str
    url: str
    quality: str
    format_type: str
    user_session: str
    created_at: float
    status: str = "pending"
    file_path: Optional[str] = None
    error: Optional[str] = None


class ConcurrentDownloadManager:
    """Manages concurrent downloads to prevent file conflicts and optimize resource usage."""
    
    def __init__(self):
        self._active_downloads: Dict[str, DownloadJob] = {}
        self._download_locks: Dict[str, asyncio.Lock] = {}
        self._user_queues: Dict[str, List[str]] = {}  # user_session -> job_ids
        self._video_jobs: Dict[str, Set[str]] = {}  # video_key -> job_ids
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_jobs())
    
    def _generate_video_key(self, url: str, quality: str, format_type: str) -> str:
        """Generate unique key for video+quality+format combination."""
        key_string = f"{url}:{quality}:{format_type}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _generate_unique_filename(self, base_name: str, extension: str, video_key: str) -> str:
        """Generate unique filename to avoid conflicts."""
        timestamp = int(time.time() * 1000)  # milliseconds
        process_id = os.getpid()
        unique_id = str(uuid.uuid4())[:8]
        
        # Create filename with timestamp and unique identifiers
        safe_base = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_base:
            safe_base = "video"
        
        unique_filename = f"{safe_base}_{timestamp}_{process_id}_{unique_id}.{extension}"
        return unique_filename
    
    async def _get_download_lock(self, video_key: str) -> asyncio.Lock:
        """Get or create download lock for video key."""
        if video_key not in self._download_locks:
            self._download_locks[video_key] = asyncio.Lock()
        return self._download_locks[video_key]
    
    async def submit_download_job(
        self,
        url: str,
        quality: str,
        format_type: str,
        user_session: str,
        custom_filename: Optional[str] = None
    ) -> str:
        """Submit a new download job and return job ID."""
        
        video_key = self._generate_video_key(url, quality, format_type)
        job_id = str(uuid.uuid4())
        
        # Extract video ID from URL for identification
        video_id = self._extract_video_id(url)
        
        # Create download job
        job = DownloadJob(
            job_id=job_id,
            video_id=video_id,
            url=url,
            quality=quality,
            format_type=format_type,
            user_session=user_session,
            created_at=time.time()
        )
        
        # Store job
        self._active_downloads[job_id] = job
        
        # Track user jobs
        if user_session not in self._user_queues:
            self._user_queues[user_session] = []
        self._user_queues[user_session].append(job_id)
        
        # Track video jobs
        if video_key not in self._video_jobs:
            self._video_jobs[video_key] = set()
        self._video_jobs[video_key].add(job_id)
        
        logger.info(f"Submitted download job {job_id} for video {video_id} by user {user_session}")
        
        return job_id
    
    async def process_download_job(self, job_id: str, download_func, **kwargs) -> Dict[str, Any]:
        """Process a download job with concurrent access management."""
        
        if job_id not in self._active_downloads:
            raise ValueError(f"Download job {job_id} not found")
        
        job = self._active_downloads[job_id]
        video_key = self._generate_video_key(job.url, job.quality, job.format_type)
        
        # Get download lock for this video+quality+format combination
        download_lock = await self._get_download_lock(video_key)
        
        try:
            async with download_lock:
                # Check if another job for the same video is already completed
                existing_file = await self._check_existing_download(video_key)
                if existing_file and os.path.exists(existing_file):
                    logger.info(f"Reusing existing download for job {job_id}: {existing_file}")
                    job.status = "completed"
                    job.file_path = existing_file
                    return {
                        "job_id": job_id,
                        "status": "completed",
                        "file_path": existing_file,
                        "reused": True
                    }
                
                # Update job status
                job.status = "processing"
                
                # Generate unique filename
                base_name = kwargs.get('custom_filename') or f"{job.video_id}"
                extension = job.format_type.lower()
                unique_filename = self._generate_unique_filename(base_name, extension, video_key)
                
                # Create unique output path
                output_dir = Path(settings.download_path) / "concurrent"
                output_dir.mkdir(parents=True, exist_ok=True)
                unique_output_path = output_dir / unique_filename
                
                # Update download options with unique filename
                kwargs['output_path'] = str(unique_output_path)
                kwargs['unique_filename'] = unique_filename
                
                logger.info(f"Processing download job {job_id} with unique filename: {unique_filename}")
                
                # Execute the actual download
                result = await download_func(job.url, **kwargs)
                
                # Update job with result
                job.status = "completed"
                job.file_path = str(unique_output_path)
                
                # Cache the successful download for reuse
                await self._cache_successful_download(video_key, str(unique_output_path))
                
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "file_path": str(unique_output_path),
                    "unique_filename": unique_filename,
                    "reused": False
                }
                
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error(f"Download job {job_id} failed: {e}")
            raise
        
        finally:
            # Clean up job tracking
            await self._cleanup_job(job_id)
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a download job."""
        if job_id not in self._active_downloads:
            return None
        
        job = self._active_downloads[job_id]
        return {
            "job_id": job.job_id,
            "video_id": job.video_id,
            "url": job.url,
            "quality": job.quality,
            "format_type": job.format_type,
            "status": job.status,
            "created_at": job.created_at,
            "file_path": job.file_path,
            "error": job.error
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a download job."""
        if job_id not in self._active_downloads:
            return False
        
        job = self._active_downloads[job_id]
        job.status = "cancelled"
        
        await self._cleanup_job(job_id)
        logger.info(f"Cancelled download job {job_id}")
        return True
    
    async def get_user_jobs(self, user_session: str) -> List[Dict[str, Any]]:
        """Get all jobs for a user session."""
        if user_session not in self._user_queues:
            return []
        
        jobs = []
        for job_id in self._user_queues[user_session]:
            if job_id in self._active_downloads:
                job_status = await self.get_job_status(job_id)
                if job_status:
                    jobs.append(job_status)
        
        return jobs
    
    async def get_concurrent_stats(self) -> Dict[str, Any]:
        """Get statistics about concurrent downloads."""
        total_jobs = len(self._active_downloads)
        status_counts = {}
        
        for job in self._active_downloads.values():
            status_counts[job.status] = status_counts.get(job.status, 0) + 1
        
        return {
            "total_active_jobs": total_jobs,
            "status_breakdown": status_counts,
            "active_locks": len(self._download_locks),
            "unique_videos": len(self._video_jobs),
            "active_users": len(self._user_queues)
        }
    
    async def _check_existing_download(self, video_key: str) -> Optional[str]:
        """Check if there's an existing completed download for the same video."""
        try:
            cache_key = f"completed_download:{video_key}"
            cached_path = await redis_service.get(cache_key)
            
            if cached_path and os.path.exists(cached_path):
                # Verify file is not corrupted (basic size check)
                file_size = os.path.getsize(cached_path)
                if file_size > 1024:  # At least 1KB
                    return cached_path
            
            return None
        except Exception as e:
            logger.debug(f"Error checking existing download: {e}")
            return None
    
    async def _cache_successful_download(self, video_key: str, file_path: str):
        """Cache information about successful download for reuse."""
        try:
            cache_key = f"completed_download:{video_key}"
            # Cache for 1 hour
            await redis_service.setex(cache_key, 3600, file_path)
        except Exception as e:
            logger.debug(f"Error caching successful download: {e}")
    
    async def _cleanup_job(self, job_id: str):
        """Clean up job from tracking structures."""
        if job_id not in self._active_downloads:
            return
        
        job = self._active_downloads[job_id]
        video_key = self._generate_video_key(job.url, job.quality, job.format_type)
        
        # Remove from video jobs tracking
        if video_key in self._video_jobs:
            self._video_jobs[video_key].discard(job_id)
            if not self._video_jobs[video_key]:
                del self._video_jobs[video_key]
                # Clean up lock if no more jobs for this video
                if video_key in self._download_locks:
                    del self._download_locks[video_key]
        
        # Remove from user queue
        if job.user_session in self._user_queues:
            try:
                self._user_queues[job.user_session].remove(job_id)
                if not self._user_queues[job.user_session]:
                    del self._user_queues[job.user_session]
            except ValueError:
                pass  # Job already removed
        
        # Remove the job itself
        del self._active_downloads[job_id]
    
    async def _cleanup_expired_jobs(self):
        """Background task to clean up expired jobs."""
        while True:
            try:
                current_time = time.time()
                expired_jobs = []
                
                for job_id, job in self._active_downloads.items():
                    # Clean up jobs older than 1 hour
                    if current_time - job.created_at > 3600:
                        expired_jobs.append(job_id)
                
                for job_id in expired_jobs:
                    logger.info(f"Cleaning up expired job {job_id}")
                    await self._cleanup_job(job_id)
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Shorter sleep on error
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from URL for identification."""
        # This is a simplified extraction - you might want to use more sophisticated logic
        import re
        
        # YouTube
        youtube_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)', url)
        if youtube_match:
            return youtube_match.group(1)
        
        # BiliBili
        bilibili_match = re.search(r'bilibili\.com/video/([^/?#]+)', url)
        if bilibili_match:
            return bilibili_match.group(1)
        
        # Fallback: use hash of URL
        return hashlib.md5(url.encode()).hexdigest()[:12]


# Global instance
concurrent_download_manager = ConcurrentDownloadManager()
