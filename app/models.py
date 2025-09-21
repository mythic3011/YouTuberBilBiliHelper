"""Pydantic models for API request/response schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl, field_validator
from enum import Enum


class VideoQuality(str, Enum):
    """Available video quality options."""
    HIGHEST = "highest"
    LOWEST = "lowest"
    BEST_AUDIO = "bestaudio"
    BEST_VIDEO = "bestvideo"
    CUSTOM = "custom"


class VideoFormat(str, Enum):
    """Supported video formats."""
    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    MP3 = "mp3"  # Audio only
    M4A = "m4a"  # Audio only


class UnityPlayerType(str, Enum):
    """Unity video player types for optimization."""
    AVPRO = "avpro"
    UNITY_VIDEO = "unity_video"
    AUTO = "auto"


class VideoCodec(str, Enum):
    """Video codecs for Unity/AVPro compatibility."""
    H264 = "h264"
    H265 = "h265"
    VP8 = "vp8"
    VP9 = "vp9"
    AV1 = "av1"


class AudioCodec(str, Enum):
    """Audio codecs for Unity/AVPro compatibility."""
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"
    VORBIS = "vorbis"


class DownloadRequest(BaseModel):
    """Request model for video downloads."""
    url: HttpUrl
    quality: VideoQuality = VideoQuality.HIGHEST
    format: VideoFormat = VideoFormat.MP4
    audio_only: bool = False
    custom_filename: Optional[str] = None
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        url_str = str(v)
        allowed_domains = [
            'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be',
            'bilibili.com', 'www.bilibili.com', 'b23.tv'
        ]
        if not any(domain in url_str for domain in allowed_domains):
            raise ValueError('URL must be from YouTube or BiliBili')
        return v


class StreamRequest(BaseModel):
    """Request model for video streaming."""
    url: HttpUrl
    quality: VideoQuality = VideoQuality.HIGHEST
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        url_str = str(v)
        allowed_domains = [
            'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be',
            'bilibili.com', 'www.bilibili.com', 'b23.tv'
        ]
        if not any(domain in url_str for domain in allowed_domains):
            raise ValueError('URL must be from YouTube or BiliBili')
        return v


class VideoInfo(BaseModel):
    """Video information model."""
    id: str
    title: str
    description: Optional[str] = None
    duration: Optional[float] = None  # in seconds (allow float from yt-dlp)
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail: Optional[str] = None
    formats: List[Dict[str, Any]] = []


class DownloadResponse(BaseModel):
    """Response model for download operations."""
    task_id: str
    status: str
    message: str
    video_info: Optional[VideoInfo] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None


class StreamResponse(BaseModel):
    """Response model for streaming operations."""
    stream_url: str
    video_info: VideoInfo
    expires_at: Optional[str] = None


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TaskInfo(BaseModel):
    """Task information model."""
    task_id: str
    status: TaskStatus
    progress: Optional[float] = None  # 0.0 to 1.0
    message: Optional[str] = None
    created_at: str
    updated_at: str
    video_info: Optional[VideoInfo] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]
    storage: Dict[str, Any]


class StorageInfo(BaseModel):
    """Storage information model."""
    total_space_gb: float
    used_space_gb: float
    available_space_gb: float
    file_count: int
    oldest_file_age_hours: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: str


class BatchDownloadRequest(BaseModel):
    """Request model for batch downloads."""
    urls: List[HttpUrl]
    quality: VideoQuality = VideoQuality.HIGHEST
    format: VideoFormat = VideoFormat.MP4
    audio_only: bool = False
    
    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        if len(v) > 10:  # Limit batch size
            raise ValueError('Maximum 10 URLs allowed per batch')
        return v


class BatchDownloadResponse(BaseModel):
    """Response model for batch downloads."""
    batch_id: str
    total_count: int
    tasks: List[DownloadResponse]
