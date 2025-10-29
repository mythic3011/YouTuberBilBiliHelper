"""File serving routes."""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.storage_service import storage_service
from app.models import ErrorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/files", tags=["files"])


@router.get("/{filename}", responses={
    200: {"description": "File download"},
    404: {"model": ErrorResponse, "description": "File not found"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def download_file(filename: str):
    """Download a file from storage."""
    try:
        # Security check - prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Try to find file in different directories
        possible_paths = [
            storage_service.youtube_dir / filename,
            storage_service.bilibili_dir / filename,
            storage_service.temp_dir / filename,
            storage_service.download_dir / filename
        ]
        
        file_path = None
        for path in possible_paths:
            if await storage_service.file_exists(path):
                file_path = path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get file info
        file_info = await storage_service.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type
        media_type = "application/octet-stream"
        if filename.lower().endswith(('.mp4', '.webm', '.mkv')):
            media_type = "video/mp4"
        elif filename.lower().endswith(('.mp3', '.m4a')):
            media_type = "audio/mpeg"
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type,
            headers={
                "Content-Length": str(file_info["size"]),
                "Accept-Ranges": "bytes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve file")


@router.head("/{filename}", responses={
    200: {"description": "File info"},
    404: {"model": ErrorResponse, "description": "File not found"}
})
async def get_file_info(filename: str):
    """Get file information without downloading."""
    try:
        # Security check
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Try to find file
        possible_paths = [
            storage_service.youtube_dir / filename,
            storage_service.bilibili_dir / filename,
            storage_service.temp_dir / filename,
            storage_service.download_dir / filename
        ]
        
        file_path = None
        for path in possible_paths:
            if await storage_service.file_exists(path):
                file_path = path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = await storage_service.get_file_info(file_path)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return headers only
        return FileResponse(
            path=str(file_path),
            filename=filename,
            headers={
                "Content-Length": str(file_info["size"]),
                "Last-Modified": str(file_info["modified"]),
                "Accept-Ranges": "bytes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file info")
