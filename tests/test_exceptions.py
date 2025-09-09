"""Tests for custom exceptions."""

import pytest
from app.exceptions import (
    APIException, RateLimitExceededError, StorageLimitExceededError,
    ValidationError, UnsupportedURLError, VideoNotFoundError,
    DownloadError, TaskNotFoundError, ServiceUnavailableError
)


class TestAPIException:
    """Test base API exception."""
    
    def test_api_exception_creation(self):
        """Test creating API exception."""
        exc = APIException("Test error", "TEST_CODE", "Test detail")
        assert exc.message == "Test error"
        assert exc.code == "TEST_CODE"
        assert exc.detail == "Test detail"
        assert str(exc) == "Test error"
        
    def test_api_exception_defaults(self):
        """Test API exception with defaults."""
        exc = APIException("Test error")
        assert exc.message == "Test error"
        assert exc.code == "API_ERROR"
        assert exc.detail == "An error occurred"


class TestRateLimitExceededError:
    """Test rate limit exceeded error."""
    
    def test_rate_limit_error_creation(self):
        """Test creating rate limit error."""
        exc = RateLimitExceededError("Rate limit exceeded", "RATE_LIMIT", "Too many requests")
        assert exc.message == "Rate limit exceeded"
        assert exc.code == "RATE_LIMIT"
        assert exc.detail == "Too many requests"
        
    def test_rate_limit_error_defaults(self):
        """Test rate limit error with defaults."""
        exc = RateLimitExceededError()
        assert "rate limit" in exc.message.lower()
        assert exc.code == "RATE_LIMIT_EXCEEDED"


class TestStorageLimitExceededError:
    """Test storage limit exceeded error."""
    
    def test_storage_limit_error_creation(self):
        """Test creating storage limit error."""
        exc = StorageLimitExceededError("Storage full", "STORAGE_FULL", "No space left")
        assert exc.message == "Storage full"
        assert exc.code == "STORAGE_FULL"
        assert exc.detail == "No space left"
        
    def test_storage_limit_error_defaults(self):
        """Test storage limit error with defaults."""
        exc = StorageLimitExceededError()
        assert "storage" in exc.message.lower()
        assert exc.code == "STORAGE_LIMIT_EXCEEDED"


class TestValidationError:
    """Test validation error."""
    
    def test_validation_error_creation(self):
        """Test creating validation error."""
        exc = ValidationError("Invalid input", "VALIDATION_ERROR", "Field is required")
        assert exc.message == "Invalid input"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.detail == "Field is required"
        
    def test_validation_error_defaults(self):
        """Test validation error with defaults."""
        exc = ValidationError()
        assert "validation" in exc.message.lower()
        assert exc.code == "VALIDATION_ERROR"


class TestUnsupportedURLError:
    """Test unsupported URL error."""
    
    def test_unsupported_url_error_creation(self):
        """Test creating unsupported URL error."""
        exc = UnsupportedURLError("URL not supported", "UNSUPPORTED_URL", "Platform not supported")
        assert exc.message == "URL not supported"
        assert exc.code == "UNSUPPORTED_URL"
        assert exc.detail == "Platform not supported"
        
    def test_unsupported_url_error_defaults(self):
        """Test unsupported URL error with defaults."""
        exc = UnsupportedURLError()
        assert "url" in exc.message.lower() or "unsupported" in exc.message.lower()
        assert exc.code == "UNSUPPORTED_URL"


class TestVideoNotFoundError:
    """Test video not found error."""
    
    def test_video_not_found_error_creation(self):
        """Test creating video not found error."""
        exc = VideoNotFoundError("Video not found", "VIDEO_NOT_FOUND", "Video does not exist")
        assert exc.message == "Video not found"
        assert exc.code == "VIDEO_NOT_FOUND"
        assert exc.detail == "Video does not exist"
        
    def test_video_not_found_error_defaults(self):
        """Test video not found error with defaults."""
        exc = VideoNotFoundError()
        assert "video" in exc.message.lower() and "not found" in exc.message.lower()
        assert exc.code == "VIDEO_NOT_FOUND"


class TestDownloadError:
    """Test download error."""
    
    def test_download_error_creation(self):
        """Test creating download error."""
        exc = DownloadError("Download failed", "DOWNLOAD_ERROR", "Network error")
        assert exc.message == "Download failed"
        assert exc.code == "DOWNLOAD_ERROR"
        assert exc.detail == "Network error"
        
    def test_download_error_defaults(self):
        """Test download error with defaults."""
        exc = DownloadError()
        assert "download" in exc.message.lower()
        assert exc.code == "DOWNLOAD_ERROR"


class TestTaskNotFoundError:
    """Test task not found error."""
    
    def test_task_not_found_error_creation(self):
        """Test creating task not found error."""
        exc = TaskNotFoundError("Task not found", "TASK_NOT_FOUND", "Task ID invalid")
        assert exc.message == "Task not found"
        assert exc.code == "TASK_NOT_FOUND"
        assert exc.detail == "Task ID invalid"
        
    def test_task_not_found_error_defaults(self):
        """Test task not found error with defaults."""
        exc = TaskNotFoundError()
        assert "task" in exc.message.lower() and "not found" in exc.message.lower()
        assert exc.code == "TASK_NOT_FOUND"


class TestServiceUnavailableError:
    """Test service unavailable error."""
    
    def test_service_unavailable_error_creation(self):
        """Test creating service unavailable error."""
        exc = ServiceUnavailableError("Service down", "SERVICE_DOWN", "Maintenance mode")
        assert exc.message == "Service down"
        assert exc.code == "SERVICE_DOWN"
        assert exc.detail == "Maintenance mode"
        
    def test_service_unavailable_error_defaults(self):
        """Test service unavailable error with defaults."""
        exc = ServiceUnavailableError()
        assert "service" in exc.message.lower() or "unavailable" in exc.message.lower()
        assert exc.code == "SERVICE_UNAVAILABLE"


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""
    
    def test_all_exceptions_inherit_from_api_exception(self):
        """Test that all custom exceptions inherit from APIException."""
        exceptions = [
            RateLimitExceededError(),
            StorageLimitExceededError(),
            ValidationError(),
            UnsupportedURLError(),
            VideoNotFoundError(),
            DownloadError(),
            TaskNotFoundError(),
            ServiceUnavailableError()
        ]
        
        for exc in exceptions:
            assert isinstance(exc, APIException)
            
    def test_exception_string_representation(self):
        """Test string representation of exceptions."""
        exceptions = [
            APIException("Test message"),
            RateLimitExceededError("Rate limit"),
            VideoNotFoundError("Video not found")
        ]
        
        for exc in exceptions:
            str_repr = str(exc)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
