"""Storage management service."""

import os
import time
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import settings
from app.exceptions import StorageLimitExceededError
from app.models import StorageInfo
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage and cleanup."""
    
    def __init__(self):
        self.download_dir = Path(settings.download_directory)
        self.youtube_dir = self.download_dir / "youtube"
        self.bilibili_dir = self.download_dir / "bilibili"
        self.temp_dir = self.download_dir / "temp"
        
        # Ensure directories exist
        for directory in [self.download_dir, self.youtube_dir, self.bilibili_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def get_storage_info(self) -> StorageInfo:
        """Get current storage information."""
        try:
            total_space = shutil.disk_usage(self.download_dir).total
            used_space = await self._get_directory_size(self.download_dir)
            available_space = total_space - used_space
            file_count = await self._count_files(self.download_dir)
            oldest_file_age = await self._get_oldest_file_age_hours()
            
            return StorageInfo(
                total_space_gb=total_space / (1024**3),
                used_space_gb=used_space / (1024**3),
                available_space_gb=available_space / (1024**3),
                file_count=file_count,
                oldest_file_age_hours=oldest_file_age
            )
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            raise
    
    async def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory."""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, FileNotFoundError):
                        # File might have been deleted, skip it
                        continue
        except Exception as e:
            logger.warning(f"Error calculating directory size: {e}")
        return total_size
    
    async def _count_files(self, directory: Path) -> int:
        """Count total number of files in directory."""
        count = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    count += 1
        except Exception as e:
            logger.warning(f"Error counting files: {e}")
        return count
    
    async def _get_oldest_file_age_hours(self) -> Optional[float]:
        """Get age of oldest file in hours."""
        try:
            oldest_mtime = None
            for file_path in self.download_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        mtime = file_path.stat().st_mtime
                        if oldest_mtime is None or mtime < oldest_mtime:
                            oldest_mtime = mtime
                    except (OSError, FileNotFoundError):
                        continue
            
            if oldest_mtime:
                age_seconds = time.time() - oldest_mtime
                return age_seconds / 3600
            return None
        except Exception as e:
            logger.warning(f"Error getting oldest file age: {e}")
            return None
    
    async def ensure_storage_available(self, required_bytes: Optional[int] = None) -> None:
        """Ensure storage limits are enforced."""
        try:
            current_size = await self._get_directory_size(self.download_dir)
            max_bytes = settings.max_storage_bytes
            
            if required_bytes:
                max_bytes -= required_bytes
            
            if current_size > max_bytes:
                logger.warning(
                    f"Storage limit exceeded. Current: {current_size / (1024**3):.2f} GB, "
                    f"Limit: {settings.max_storage_gb} GB"
                )
                await self._cleanup_old_files(current_size - max_bytes)
        except Exception as e:
            logger.error(f"Error ensuring storage available: {e}")
            raise StorageLimitExceededError(
                "Storage management failed",
                code="STORAGE_ERROR",
                detail=str(e)
            )
    
    async def _cleanup_old_files(self, bytes_to_free: int) -> None:
        """Clean up old files to free specified amount of space."""
        try:
            # Get all files with modification times
            files_with_mtime = []
            for file_path in self.download_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        files_with_mtime.append((file_path, stat.st_mtime, stat.st_size))
                    except (OSError, FileNotFoundError):
                        continue
            
            # Sort by modification time (oldest first)
            files_with_mtime.sort(key=lambda x: x[1])
            
            freed_bytes = 0
            deleted_count = 0
            
            for file_path, mtime, size in files_with_mtime:
                try:
                    file_path.unlink()
                    freed_bytes += size
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file_path}")
                    
                    if freed_bytes >= bytes_to_free:
                        break
                except (OSError, FileNotFoundError) as e:
                    logger.warning(f"Could not delete file {file_path}: {e}")
                    continue
            
            logger.info(
                f"Cleanup completed. Deleted {deleted_count} files, "
                f"freed {freed_bytes / (1024**2):.2f} MB"
            )
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise
    
    async def cleanup_expired_files(self) -> None:
        """Clean up files older than retention period."""
        try:
            retention_seconds = settings.temp_file_retention_hours * 3600
            current_time = time.time()
            cutoff_time = current_time - retention_seconds
            
            deleted_count = 0
            freed_bytes = 0
            
            for file_path in self.download_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        if stat.st_mtime < cutoff_time:
                            size = stat.st_size
                            file_path.unlink()
                            freed_bytes += size
                            deleted_count += 1
                            logger.debug(f"Deleted expired file: {file_path}")
                    except (OSError, FileNotFoundError):
                        continue
            
            if deleted_count > 0:
                logger.info(
                    f"Expired file cleanup: deleted {deleted_count} files, "
                    f"freed {freed_bytes / (1024**2):.2f} MB"
                )
                
        except Exception as e:
            logger.error(f"Error during expired file cleanup: {e}")
    
    def get_file_path(self, platform: str, filename: str) -> Path:
        """Get full file path for a given platform and filename."""
        if platform.lower() == "youtube":
            return self.youtube_dir / filename
        elif platform.lower() == "bilibili":
            return self.bilibili_dir / filename
        else:
            return self.temp_dir / filename
    
    def get_temp_file_path(self, filename: str) -> Path:
        """Get temporary file path."""
        return self.temp_dir / filename
    
    async def file_exists(self, file_path: Path) -> bool:
        """Check if file exists asynchronously."""
        try:
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False
    
    async def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get file information."""
        try:
            if not await self.file_exists(file_path):
                return None
            
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "name": file_path.name,
                "path": str(file_path)
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None


# Global storage service instance
storage_service = StorageService()
