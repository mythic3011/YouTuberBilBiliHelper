"""
Example unit tests demonstrating best practices.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestExampleUnit:
    """Example unit tests."""

    def test_simple_assertion(self):
        """Test simple assertion."""
        assert 1 + 1 == 2

    def test_with_fixture(self, sample_video_data):
        """Test using a fixture."""
        assert sample_video_data["platform"] == "youtube"
        assert sample_video_data["duration"] > 0

    @pytest.mark.parametrize("input,expected", [
        ("youtube", True),
        ("bilibili", True),
        ("invalid", False),
    ])
    def test_platform_validation(self, input, expected):
        """Test platform validation with parameters."""
        valid_platforms = ["youtube", "bilibili", "twitter", "instagram"]
        result = input in valid_platforms
        assert result == expected

    def test_with_mock(self):
        """Test with mock object."""
        mock_service = Mock()
        mock_service.get_video.return_value = {"id": "123", "title": "Test"}

        result = mock_service.get_video("123")

        assert result["id"] == "123"
        mock_service.get_video.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async function."""
        async def async_add(a, b):
            return a + b

        result = await async_add(2, 3)
        assert result == 5


class TestExampleEdgeCases:
    """Example tests for edge cases."""

    def test_empty_string(self):
        """Test empty string handling."""
        result = "".strip()
        assert result == ""

    def test_none_value(self):
        """Test None value handling."""
        result = None
        assert result is None

    def test_list_operations(self):
        """Test list operations."""
        items = [1, 2, 3]
        items.append(4)
        assert len(items) == 4
        assert 4 in items


class TestExampleExceptions:
    """Example tests for exception handling."""

    def test_raises_exception(self):
        """Test that exception is raised."""
        with pytest.raises(ValueError):
            raise ValueError("Test error")

    def test_exception_message(self):
        """Test exception message."""
        with pytest.raises(ValueError, match="Test error"):
            raise ValueError("Test error")
