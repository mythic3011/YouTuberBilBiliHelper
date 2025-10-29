"""Video routing module for video information, downloads, and batch operations."""

from app.routes.videos.info import router as info_router
from app.routes.videos.batch import router as batch_router
from app.routes.videos.concurrent import router as concurrent_router
from app.routes.videos.files import router as files_router

__all__ = ["info_router", "batch_router", "concurrent_router", "files_router"]

