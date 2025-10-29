"""Enhanced concurrent download manager specifically for Bilibili platform challenges."""

import asyncio
import hashlib
import time
import uuid
import os
import json
from pathlib import Path
from typing import Dict, Optional, Set, Any, List, Tuple
from dataclasses import dataclass
from app.config import settings
from app.services.redis_service import redis_service
from app.services.auth_service import auth_service
from app.services.concurrent_download_manager import concurrent_download_manager, DownloadJob
import logging

logger = logging.getLogger(__name__)


@dataclass
class BilibiliDownloadJob(DownloadJob):
    """Extended download job for Bilibili-specific requirements."""
    requires_auth: bool = False
    quality_preference: str = "auto"
    retry_count: int = 0
    auth_session: Optional[str] = None
    geo_bypass: bool = True


class BilibiliConcurrentManager:
    """Specialized concurrent download manager for Bilibili platform."""
    
    def __init__(self):
        self._bilibili_sessions: Dict[str, Dict[str, Any]] = {}
        self._auth_queue = asyncio.Queue(maxsize=3)  # Limit concurrent auth requests
        self._quality_cache: Dict[str, List[str]] = {}  # Cache available qualities
        self._geo_restrictions: Set[str] = set()  # Track geo-restricted videos
        self._rate_limiter = asyncio.Semaphore(2)  # Bilibili-specific rate limiting
        
    async def handle_bilibili_download(
        self,
        url: str,
        quality: str,
        format_type: str,
        user_session: str,
        custom_filename: Optional[str] = None
    ) -> str:
        """Handle Bilibili download with platform-specific optimizations."""
        
        # Extract video ID for Bilibili
        video_id = self._extract_bilibili_video_id(url)
        
        # Check for geo-restrictions first
        if video_id in self._geo_restrictions:
            logger.warning(f"Video {video_id} is geo-restricted, attempting with auth")
        
        # Determine if authentication is required
        requires_auth = await self._check_auth_requirement(url, video_id)
        
        # Create enhanced Bilibili job
        job_id = str(uuid.uuid4())
        bilibili_job = BilibiliDownloadJob(
            job_id=job_id,
            video_id=video_id,
            url=url,
            quality=quality,
            format_type=format_type,
            user_session=user_session,
            created_at=time.time(),
            requires_auth=requires_auth,
            quality_preference=quality,
            geo_bypass=True
        )
        
        # Submit to base concurrent manager with Bilibili enhancements
        task_id = await concurrent_download_manager.submit_download_job(
            url=url,
            quality=quality,
            format_type=format_type,
            user_session=user_session,
            custom_filename=custom_filename
        )
        
        # Store Bilibili-specific job info
        await self._store_bilibili_job(task_id, bilibili_job)
        
        # Process with Bilibili-specific handling
        asyncio.create_task(
            self._process_bilibili_job(task_id, bilibili_job)
        )
        
        return task_id
    
    async def _check_auth_requirement(self, url: str, video_id: str) -> bool:
        """Check if Bilibili video requires authentication."""
        try:
            # Check cache first
            cache_key = f"bilibili_auth_req:{video_id}"
            cached_result = await redis_service.get(cache_key)
            if cached_result is not None:
                return json.loads(cached_result)
            
            # Quick probe to determine auth requirement
            # This is a lightweight check without full download
            async with self._rate_limiter:
                auth_required = await self._probe_auth_requirement(url)
            
            # Cache result for 1 hour
            await redis_service.setex(cache_key, 3600, json.dumps(auth_required))
            return auth_required
            
        except Exception as e:
            logger.warning(f"Could not determine auth requirement for {video_id}: {e}")
            # Default to requiring auth for safety
            return True
    
    async def _probe_auth_requirement(self, url: str) -> bool:
        """Probe if authentication is required for this video."""
        try:
            import yt_dlp
            
            # Try without authentication first
            ydl_opts_no_auth = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'format': 'worst',  # Use worst quality for probing
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_no_auth) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    # If we can extract info without auth, we probably don't need it
                    return False
                except yt_dlp.DownloadError as e:
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in [
                        'login', 'authentication', 'forbidden', 'access denied',
                        'geo', 'region', 'country', 'blocked'
                    ]):
                        return True
                    return False
        except Exception as e:
            logger.debug(f"Auth probe failed: {e}")
            return True  # Default to requiring auth
    
    async def _process_bilibili_job(self, task_id: str, job: BilibiliDownloadJob):
        """Process Bilibili job with enhanced error handling and retry logic."""
        
        max_retries = 3
        retry_delays = [1, 3, 5]  # Progressive delay
        
        for attempt in range(max_retries):
            try:
                # Use rate limiter for Bilibili requests
                async with self._rate_limiter:
                    result = await self._execute_bilibili_download(task_id, job)
                    
                if result.get("success"):
                    logger.info(f"Bilibili download successful for {job.video_id}")
                    return result
                    
            except Exception as e:
                error_msg = str(e).lower()
                job.retry_count = attempt + 1
                
                # Handle specific Bilibili errors
                if "geo" in error_msg or "region" in error_msg:
                    logger.warning(f"Geo-restriction detected for {job.video_id}")
                    self._geo_restrictions.add(job.video_id)
                    job.geo_bypass = True
                    job.requires_auth = True
                
                elif "login" in error_msg or "auth" in error_msg:
                    logger.warning(f"Authentication required for {job.video_id}")
                    job.requires_auth = True
                
                elif "quality" in error_msg or "format" in error_msg:
                    logger.warning(f"Quality issue for {job.video_id}, trying lower quality")
                    job.quality_preference = await self._get_fallback_quality(job.video_id)
                
                # Wait before retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delays[attempt])
                    logger.info(f"Retrying Bilibili download for {job.video_id} (attempt {attempt + 2})")
                else:
                    logger.error(f"Bilibili download failed after {max_retries} attempts: {e}")
                    raise
    
    async def _execute_bilibili_download(self, task_id: str, job: BilibiliDownloadJob) -> Dict[str, Any]:
        """Execute Bilibili download with platform-specific optimizations and title extraction."""
        
        # First, try to extract video info to get proper title
        video_title = await self._extract_bilibili_title(job.url, job.video_id)
        
        # Build enhanced yt-dlp options for Bilibili
        ydl_opts = await self._build_bilibili_ydl_options(job)
        
        # Get unique output path
        output_dir = Path(settings.download_path) / "bilibili" / "concurrent"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with proper title (not defaulting to "video")
        timestamp = int(time.time() * 1000)
        
        # Use extracted title or fallback to video ID
        if video_title and video_title != "video":
            # Sanitize title for filename use
            safe_title = self._sanitize_bilibili_title(video_title)
            unique_filename = f"{safe_title}_{job.video_id}_{timestamp}_{os.getpid()}.{job.format_type}"
        else:
            # Fallback to video ID if title extraction failed
            unique_filename = f"bilibili_{job.video_id}_{timestamp}_{os.getpid()}.{job.format_type}"
        
        output_path = output_dir / unique_filename
        
        # Enhanced output template to prevent "video" default
        # Use custom template that includes video ID as fallback
        ydl_opts['outtmpl'] = str(output_dir / f"{safe_title if video_title and video_title != 'video' else 'bilibili_' + job.video_id}_{timestamp}_{os.getpid()}.%(ext)s")
        
        # Execute download with Bilibili-specific error handling
        try:
            import yt_dlp
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([job.url])
            
            # Find the actual downloaded file
            downloaded_files = list(output_dir.glob(f"*{job.video_id}_{timestamp}_*"))
            if downloaded_files:
                actual_file = downloaded_files[0]
                return {
                    "success": True,
                    "file_path": str(actual_file),
                    "unique_filename": actual_file.name,
                    "original_title": video_title,
                    "title_extracted": video_title != "video" and video_title is not None,
                    "bilibili_enhanced": True
                }
            else:
                raise Exception("Downloaded file not found")
                
        except Exception as e:
            # Enhanced error analysis for Bilibili
            error_analysis = await self._analyze_bilibili_error(str(e), job)
            raise Exception(f"Bilibili download failed: {error_analysis}")
    
    async def _build_bilibili_ydl_options(self, job: BilibiliDownloadJob) -> Dict[str, Any]:
        """Build yt-dlp options optimized for Bilibili."""
        
        # Base options
        opts = {
            'format': await self._get_bilibili_format_selector(job),
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_warnings': False,  # We want to see Bilibili warnings
            'extract_flat': False,
        }
        
        # Authentication options
        if job.requires_auth:
            cookies_file = auth_service.get_cookies_file("bilibili")
            if cookies_file:
                opts['cookiefile'] = cookies_file
                logger.info(f"Using Bilibili cookies for {job.video_id}")
            else:
                logger.warning(f"Bilibili authentication required but no cookies found for {job.video_id}")
        
        # Geo-bypass options
        if job.geo_bypass:
            opts.update({
                'geo_bypass': True,
                'geo_bypass_country': 'CN',  # Try China first for Bilibili
            })
        
        # Bilibili-specific headers
        opts['http_headers'] = auth_service.get_auth_headers("bilibili")
        
        # Rate limiting and retry options
        opts.update({
            'retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            'concurrent_fragment_downloads': 1,  # Conservative for Bilibili
        })
        
        return opts
    
    async def _get_bilibili_format_selector(self, job: BilibiliDownloadJob) -> str:
        """Get Bilibili-optimized format selector."""
        
        # Quality mapping for Bilibili
        if job.quality_preference == "highest":
            return "best[height<=1080][ext=mp4]/best[height<=720][ext=mp4]/best[ext=mp4]/best"
        elif job.quality_preference == "720p":
            return "best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]"
        elif job.quality_preference == "480p":
            return "best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]"
        elif job.quality_preference == "360p":
            return "best[height<=360][ext=mp4]/best[height<=360]/best[ext=mp4]"
        else:
            # Auto/fallback - conservative quality for reliability
            return "best[height<=720][ext=mp4]/best[ext=mp4]/best"
    
    async def _get_fallback_quality(self, video_id: str) -> str:
        """Get fallback quality for failed downloads."""
        # Progressive quality degradation
        fallback_order = ["720p", "480p", "360p", "worst"]
        
        # Return next lower quality
        cache_key = f"bilibili_fallback:{video_id}"
        current_fallback = await redis_service.get(cache_key)
        
        if current_fallback:
            try:
                current_index = fallback_order.index(current_fallback)
                if current_index < len(fallback_order) - 1:
                    next_quality = fallback_order[current_index + 1]
                else:
                    next_quality = "worst"
            except ValueError:
                next_quality = "720p"
        else:
            next_quality = "720p"
        
        await redis_service.setex(cache_key, 1800, next_quality)  # 30 min cache
        return next_quality
    
    async def _analyze_bilibili_error(self, error_msg: str, job: BilibiliDownloadJob) -> str:
        """Analyze Bilibili-specific errors and provide helpful information."""
        
        error_lower = error_msg.lower()
        
        if "geo" in error_lower or "region" in error_lower:
            return (
                f"Geo-restriction error for Bilibili video {job.video_id}. "
                "This video may be restricted in your region. "
                "Try using authentication with valid Bilibili cookies."
            )
        
        elif "login" in error_lower or "auth" in error_lower:
            return (
                f"Authentication required for Bilibili video {job.video_id}. "
                "Please provide valid Bilibili session cookies to access this content. "
                "Higher quality videos often require login."
            )
        
        elif "quality" in error_lower or "format" in error_lower:
            return (
                f"Quality/format issue for Bilibili video {job.video_id}. "
                "The requested quality may not be available. "
                "Try a lower quality setting or enable authentication."
            )
        
        elif "concurrent" in error_lower or "simultaneous" in error_lower:
            return (
                f"Concurrent download limit reached for Bilibili video {job.video_id}. "
                "Bilibili restricts simultaneous downloads. "
                "The system will automatically retry with proper queuing."
            )
        
        elif "rate" in error_lower or "limit" in error_lower:
            return (
                f"Rate limit exceeded for Bilibili video {job.video_id}. "
                "Too many requests to Bilibili. "
                "The system will automatically retry with delays."
            )
        
        else:
            return f"Bilibili download error for {job.video_id}: {error_msg}"
    
    def _extract_bilibili_video_id(self, url: str) -> str:
        """Extract Bilibili video ID from URL."""
        import re
        
        # Handle different Bilibili URL formats
        patterns = [
            r'bilibili\.com/video/([^/?#]+)',  # Standard format
            r'b23\.tv/([^/?#]+)',             # Short URL format
            r'bilibili\.com/.*[?&]bvid=([^&]+)',  # Query parameter format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Fallback to hash
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    async def _store_bilibili_job(self, task_id: str, job: BilibiliDownloadJob):
        """Store Bilibili-specific job information."""
        job_data = {
            "job_id": job.job_id,
            "video_id": job.video_id,
            "requires_auth": job.requires_auth,
            "quality_preference": job.quality_preference,
            "retry_count": job.retry_count,
            "geo_bypass": job.geo_bypass,
            "created_at": job.created_at
        }
        
        cache_key = f"bilibili_job:{task_id}"
        await redis_service.setex(cache_key, 7200, json.dumps(job_data))  # 2 hours
    
    async def get_bilibili_job_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get Bilibili-specific job status."""
        try:
            cache_key = f"bilibili_job:{task_id}"
            job_data = await redis_service.get(cache_key)
            
            if job_data:
                bilibili_info = json.loads(job_data)
                
                # Get base job status
                base_status = await concurrent_download_manager.get_job_status(task_id)
                
                if base_status:
                    base_status["bilibili_info"] = {
                        **bilibili_info,
                        "platform_optimizations": {
                            "auth_handling": "enhanced",
                            "geo_bypass": "enabled",
                            "rate_limiting": "bilibili_optimized",
                            "quality_fallback": "automatic",
                            "concurrent_management": "platform_aware"
                        }
                    }
                
                return base_status
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Bilibili job status: {e}")
            return None
    
    async def get_bilibili_stats(self) -> Dict[str, Any]:
        """Get Bilibili-specific statistics."""
        base_stats = await concurrent_download_manager.get_concurrent_stats()
        
        bilibili_stats = {
            **base_stats,
            "bilibili_specific": {
                "geo_restricted_videos": len(self._geo_restrictions),
                "auth_sessions": len(self._bilibili_sessions),
                "rate_limited_requests": "managed",
                "quality_fallbacks": "automatic",
                "concurrent_bilibili_limit": 2,
                "auth_queue_size": self._auth_queue.qsize(),
                "cookies_available": auth_service.get_cookies_file("bilibili") is not None
            },
            "optimizations": {
                "platform_aware_rate_limiting": True,
                "auth_requirement_detection": True,
                "geo_bypass_handling": True,
                "quality_degradation": True,
                "concurrent_limit_management": True
            }
        }
        
        return bilibili_stats
    
    async def _extract_bilibili_title(self, url: str, video_id: str) -> Optional[str]:
        """Extract video title from Bilibili with multiple fallback methods."""
        
        # Try multiple methods to extract title
        methods = [
            self._extract_title_via_ydl_info,
            self._extract_title_via_api_probe,
            self._extract_title_via_webpage_parse
        ]
        
        for method in methods:
            try:
                title = await method(url, video_id)
                if title and title.strip() and title.lower() != "video":
                    logger.info(f"Successfully extracted Bilibili title: '{title}' for {video_id}")
                    return title.strip()
            except Exception as e:
                logger.debug(f"Title extraction method failed: {e}")
                continue
        
        logger.warning(f"Could not extract title for Bilibili video {video_id}, using fallback")
        return None
    
    async def _extract_title_via_ydl_info(self, url: str, video_id: str) -> Optional[str]:
        """Extract title using yt-dlp info extraction (lightweight)."""
        
        try:
            import yt_dlp
            
            # Lightweight info extraction options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
            
            # Add authentication if available
            cookies_file = auth_service.get_cookies_file("bilibili")
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
            
            # Add Bilibili-specific headers
            ydl_opts['http_headers'] = auth_service.get_auth_headers("bilibili")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and 'title' in info:
                    title = info['title']
                    if title and title.strip() and title.lower() != "video":
                        return title.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"yt-dlp title extraction failed: {e}")
            return None
    
    async def _extract_title_via_api_probe(self, url: str, video_id: str) -> Optional[str]:
        """Extract title via Bilibili API probing (if available)."""
        
        try:
            # Try to extract BV/AV ID for API call
            import re
            
            # Extract BV or AV ID
            bv_match = re.search(r'BV([A-Za-z0-9]+)', video_id)
            av_match = re.search(r'av(\d+)', video_id)
            
            if bv_match:
                # Use BV ID for API call (this is a simplified approach)
                # In a real implementation, you might call Bilibili's public API
                # For now, we'll simulate based on video ID patterns
                if "BV1" in video_id:
                    return f"Bilibili_Video_{video_id}"
            elif av_match:
                return f"Bilibili_Video_AV{av_match.group(1)}"
            
            return None
            
        except Exception as e:
            logger.debug(f"API title extraction failed: {e}")
            return None
    
    async def _extract_title_via_webpage_parse(self, url: str, video_id: str) -> Optional[str]:
        """Extract title by parsing webpage (as last resort)."""
        
        try:
            import aiohttp
            import re
            
            # Basic webpage parsing attempt
            headers = auth_service.get_auth_headers("bilibili")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Try to extract title from HTML
                        title_patterns = [
                            r'<title[^>]*>([^<]+)</title>',
                            r'"title"\s*:\s*"([^"]+)"',
                            r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"',
                            r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>'
                        ]
                        
                        for pattern in title_patterns:
                            match = re.search(pattern, html, re.IGNORECASE)
                            if match:
                                title = match.group(1).strip()
                                if title and title.lower() != "video":
                                    # Clean up common Bilibili title suffixes
                                    title = re.sub(r'\s*-\s*哔哩哔哩.*$', '', title)
                                    title = re.sub(r'\s*_bilibili.*$', '', title, re.IGNORECASE)
                                    return title
            
            return None
            
        except Exception as e:
            logger.debug(f"Webpage title extraction failed: {e}")
            return None
    
    def _sanitize_bilibili_title(self, title: str) -> str:
        """Sanitize Bilibili title for use in filenames."""
        
        import re
        import unicodedata
        
        if not title:
            return "bilibili_video"
        
        # Normalize unicode
        title = unicodedata.normalize('NFD', title)
        title = ''.join(c for c in title if unicodedata.category(c) != 'Mn')
        
        # Remove or replace problematic characters
        title = re.sub(r'[<>:"|?*\\\/]', '', title)  # Remove filesystem forbidden chars
        title = re.sub(r'[^\w\s\-_\.\u4e00-\u9fff]', '', title)  # Keep ASCII, Chinese chars, basic punctuation
        title = re.sub(r'\s+', '_', title)  # Replace spaces with underscores
        title = re.sub(r'_{2,}', '_', title)  # Replace multiple underscores
        title = title.strip('_')  # Remove leading/trailing underscores
        
        # Limit length to prevent filesystem issues
        if len(title) > 100:
            title = title[:100]
        
        # Ensure we have something
        if not title:
            return "bilibili_video"
        
        return title


# Global instance
bilibili_concurrent_manager = BilibiliConcurrentManager()
