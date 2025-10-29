"""Shared utilities for the application."""

from app.utils.responses import (
    success_response,
    error_response,
    paginated_response
)
from app.utils.decorators import (
    handle_errors,
    log_execution_time,
    cache_result,
    retry_on_failure
)
from app.utils.cache import (
    generate_cache_key,
    hash_cache_key,
    generate_video_cache_key,
    generate_stream_cache_key,
    generate_auth_cache_key,
    serialize_for_cache,
    deserialize_from_cache
)
from app.utils.validators import (
    validate_url,
    extract_video_id,
    validate_platform,
    validate_quality,
    validate_format,
    sanitize_filename,
    validate_video_id,
    validate_pagination
)

__all__ = [
    # Response builders
    "success_response",
    "error_response",
    "paginated_response",
    # Decorators
    "handle_errors",
    "log_execution_time",
    "cache_result",
    "retry_on_failure",
    # Cache utilities
    "generate_cache_key",
    "hash_cache_key",
    "generate_video_cache_key",
    "generate_stream_cache_key",
    "generate_auth_cache_key",
    "serialize_for_cache",
    "deserialize_from_cache",
    # Validators
    "validate_url",
    "extract_video_id",
    "validate_platform",
    "validate_quality",
    "validate_format",
    "sanitize_filename",
    "validate_video_id",
    "validate_pagination",
]

