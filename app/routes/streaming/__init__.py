"""Streaming routing module for video streaming endpoints."""

from app.routes.streaming.proxy import router as proxy_router
from app.routes.streaming.direct import router as direct_router

__all__ = ["proxy_router", "direct_router"]

