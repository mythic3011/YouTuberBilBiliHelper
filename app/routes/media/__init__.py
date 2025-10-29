"""Media routing module for media management and content processing."""

from app.routes.media.management import router as management_router
from app.routes.media.processing import router as processing_router

__all__ = ["management_router", "processing_router"]

