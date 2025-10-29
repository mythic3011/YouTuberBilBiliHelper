"""Cache key generation and management utilities."""

import hashlib
import json
from typing import Any, Optional


def generate_cache_key(
    prefix: str,
    *args: Any,
    **kwargs: Any
) -> str:
    """
    Generate a cache key from prefix and arguments.
    
    Args:
        prefix: Key prefix (e.g., 'video', 'stream')
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        Generated cache key
        
    Example:
        >>> generate_cache_key('video', 'youtube', 'abc123', quality='720p')
        'video:youtube:abc123:quality=720p'
    """
    parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        parts.append(str(arg))
    
    # Add keyword arguments (sorted for consistency)
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}={kwargs[key]}")
    
    return ":".join(parts)


def hash_cache_key(key: str) -> str:
    """
    Create a hashed version of a cache key.
    
    Useful for very long keys that might exceed Redis key length limits.
    
    Args:
        key: Original cache key
        
    Returns:
        SHA256 hash of the key
    """
    return hashlib.sha256(key.encode()).hexdigest()


def generate_video_cache_key(
    platform: str,
    video_id: str,
    quality: Optional[str] = None,
    format: Optional[str] = None
) -> str:
    """
    Generate a standardized cache key for video data.
    
    Args:
        platform: Platform name (youtube, bilibili, etc.)
        video_id: Video ID
        quality: Video quality
        format: Video format
        
    Returns:
        Cache key for video
    """
    return generate_cache_key(
        'video',
        platform,
        video_id,
        quality=quality or 'best',
        format=format or 'any'
    )


def generate_stream_cache_key(
    platform: str,
    video_id: str,
    quality: Optional[str] = None
) -> str:
    """
    Generate a standardized cache key for stream URLs.
    
    Args:
        platform: Platform name
        video_id: Video ID
        quality: Stream quality
        
    Returns:
        Cache key for stream URL
    """
    return generate_cache_key(
        'stream',
        platform,
        video_id,
        quality=quality or 'best'
    )


def generate_auth_cache_key(platform: str) -> str:
    """
    Generate a standardized cache key for authentication status.
    
    Args:
        platform: Platform name
        
    Returns:
        Cache key for authentication
    """
    return generate_cache_key('auth', platform)


def serialize_for_cache(data: Any) -> str:
    """
    Serialize data for caching.
    
    Args:
        data: Data to serialize
        
    Returns:
        JSON string representation
    """
    try:
        return json.dumps(data, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to serialize data for cache: {e}")


def deserialize_from_cache(data: str) -> Any:
    """
    Deserialize data from cache.
    
    Args:
        data: JSON string from cache
        
    Returns:
        Deserialized data
    """
    try:
        return json.loads(data)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to deserialize data from cache: {e}")

