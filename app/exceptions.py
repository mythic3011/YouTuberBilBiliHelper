"""Custom exceptions for the API."""

from typing import Optional


class APIException(Exception):
    """Base API exception."""
    
    def __init__(self, message: str, code: Optional[str] = None, detail: Optional[str] = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(self.message)


class ValidationError(APIException):
    """Raised when input validation fails."""
    pass


class UnsupportedURLError(APIException):
    """Raised when URL is not supported."""
    pass


class VideoNotFoundError(APIException):
    """Raised when video cannot be found."""
    pass


class DownloadError(APIException):
    """Raised when download operation fails."""
    pass


class StorageLimitExceededError(APIException):
    """Raised when storage limit is exceeded."""
    pass


class RateLimitExceededError(APIException):
    """Raised when rate limit is exceeded."""
    pass


class TaskNotFoundError(APIException):
    """Raised when task cannot be found."""
    pass


class ServiceUnavailableError(APIException):
    """Raised when external service is unavailable."""
    pass


class ConfigurationError(APIException):
    """Raised when configuration is invalid."""
    pass
