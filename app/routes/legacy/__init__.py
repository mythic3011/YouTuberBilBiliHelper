"""Legacy routing module for backward compatibility endpoints."""

from app.routes.legacy.simple import router as simple_router
from app.routes.legacy.vrchat import router as vrchat_router

__all__ = ["simple_router", "vrchat_router"]

