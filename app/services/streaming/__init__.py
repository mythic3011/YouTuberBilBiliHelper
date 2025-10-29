"""Streaming services module for video proxy and streaming functionality."""

from app.services.streaming.base_service import BaseStreamingService
from app.services.streaming.proxy_service import StreamingService
from app.services.streaming.robust_service import RobustStreamingService

# Create singleton instances
streaming_service = StreamingService()
robust_streaming_service = RobustStreamingService()

__all__ = [
    "BaseStreamingService",
    "StreamingService",
    "RobustStreamingService",
    "streaming_service",
    "robust_streaming_service"
]

