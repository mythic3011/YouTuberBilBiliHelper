"""Input validation utilities for API endpoints."""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


# Platform-specific URL patterns
YOUTUBE_PATTERNS = [
    r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
    r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
]

BILIBILI_PATTERNS = [
    r'bilibili\.com/video/(av\d+|BV[a-zA-Z0-9]+)',
    r'b23\.tv/([a-zA-Z0-9]+)',
]

TWITTER_PATTERNS = [
    r'twitter\.com/\w+/status/(\d+)',
    r'x\.com/\w+/status/(\d+)',
]

INSTAGRAM_PATTERNS = [
    r'instagram\.com/(?:p|reel)/([a-zA-Z0-9_-]+)',
]


def validate_url(url: str) -> bool:
    """
    Validate if string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_video_id(url: str, platform: Optional[str] = None) -> Optional[tuple[str, str]]:
    """
    Extract video ID and platform from URL.
    
    Args:
        url: Video URL
        platform: Expected platform (optional)
        
    Returns:
        Tuple of (platform, video_id) or None if not found
    """
    # Try YouTube
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return ('youtube', match.group(1))
    
    # Try Bilibili
    for pattern in BILIBILI_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return ('bilibili', match.group(1))
    
    # Try Twitter
    for pattern in TWITTER_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return ('twitter', match.group(1))
    
    # Try Instagram
    for pattern in INSTAGRAM_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return ('instagram', match.group(1))
    
    return None


def validate_platform(platform: str) -> bool:
    """
    Validate if platform is supported.
    
    Args:
        platform: Platform name
        
    Returns:
        True if supported, False otherwise
    """
    supported_platforms = ['youtube', 'bilibili', 'twitter', 'instagram', 'twitch']
    return platform.lower() in supported_platforms


def validate_quality(quality: str) -> bool:
    """
    Validate if quality option is valid.
    
    Args:
        quality: Quality string
        
    Returns:
        True if valid, False otherwise
    """
    valid_qualities = [
        'best', 'worst',
        '2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p',
        '4k', 'hd', 'sd'
    ]
    return quality.lower() in valid_qualities


def validate_format(format: str) -> bool:
    """
    Validate if format option is valid.
    
    Args:
        format: Format string
        
    Returns:
        True if valid, False otherwise
    """
    valid_formats = [
        'mp4', 'webm', 'mkv', 'flv', 'avi',  # Video
        'mp3', 'm4a', 'wav', 'flac', 'aac',  # Audio
    ]
    return format.lower() in valid_formats


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Trim whitespace
    filename = filename.strip()
    
    # Truncate if too long
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = max_length - len(ext) - 1
        filename = f"{name[:max_name_length]}.{ext}" if ext else name[:max_length]
    
    return filename


def validate_video_id(video_id: str, platform: str) -> bool:
    """
    Validate video ID format for specific platform.
    
    Args:
        video_id: Video ID to validate
        platform: Platform name
        
    Returns:
        True if valid format, False otherwise
    """
    if platform == 'youtube':
        return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))
    elif platform == 'bilibili':
        return bool(re.match(r'^(av\d+|BV[a-zA-Z0-9]+)$', video_id))
    elif platform == 'twitter':
        return bool(re.match(r'^\d+$', video_id))
    elif platform == 'instagram':
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', video_id))
    
    return True  # Allow other platforms


def validate_pagination(page: int, page_size: int, max_page_size: int = 100) -> tuple[bool, Optional[str]]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if page < 1:
        return (False, "Page number must be at least 1")
    
    if page_size < 1:
        return (False, "Page size must be at least 1")
    
    if page_size > max_page_size:
        return (False, f"Page size cannot exceed {max_page_size}")
    
    return (True, None)

