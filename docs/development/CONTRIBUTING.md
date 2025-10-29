# 🤝 Contributing to YouTuberBilBiliHelper

Thank you for your interest in contributing! This guide will help you get started.

---

## 🚀 Quick Start

### 1. Setup Your Environment

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/YouTuberBilBiliHelper.git
cd YouTuberBilBiliHelper

# Run automated setup
./scripts/setup-dev.sh

# Start development environment
make dev
```

**That's it!** You're ready to contribute! 🎉

---

## 📝 Development Workflow

### 1. Create a Branch

```bash
# Always create a new branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Your Changes

```bash
# Make your changes...

# Format code (happens automatically on commit)
make format

# Run tests
make test-all

# Check code quality
make quality
```

### 3. Commit Your Changes

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Good commit messages:
git commit -m "feat: add video quality selection"
git commit -m "fix: resolve streaming timeout issue"
git commit -m "docs: update API documentation"
git commit -m "test: add tests for video service"
git commit -m "refactor: simplify error handling"
git commit -m "chore: update dependencies"

# Pre-commit hooks will run automatically:
# ✓ Code formatting (black, isort)
# ✓ Linting (ruff)
# ✓ Type checking (mypy)
# ✓ Security scanning (bandit)
```

### 4. Push and Create PR

```bash
# Push your branch
git push origin feature/your-feature-name

# Create a Pull Request on GitHub
# - Describe your changes
# - Reference any related issues
# - Wait for CI checks to pass
# - Request review
```

---

## 🧪 Testing Guidelines

### Writing Tests

We use **pytest** for testing. Tests should be:
- **Fast**: Unit tests < 100ms
- **Isolated**: Don't depend on external services
- **Clear**: Descriptive test names
- **Comprehensive**: Cover edge cases

### Test Structure

```python
import pytest
from app.services.video_service import VideoService

class TestVideoService:
    """Tests for VideoService."""

    @pytest.fixture
    def video_service(self):
        """Create a VideoService instance."""
        return VideoService()

    def test_get_video_info_success(self, video_service):
        """Test getting video info successfully."""
        # Arrange
        video_id = "dQw4w9WgXcQ"

        # Act
        result = video_service.get_video_info(video_id)

        # Assert
        assert result is not None
        assert result.id == video_id
```

### Test Categories

```bash
# Unit tests (fast, isolated)
make test-unit

# Integration tests (test API endpoints)
make test-integration

# All tests with coverage
make test-all
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.slow
def test_large_download():
    """This test takes a while."""
    pass

@pytest.mark.integration
def test_api_endpoint():
    """This is an integration test."""
    pass
```

---

## 🎨 Code Style Guide

### Python Style

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Formatting**: Automatic with `black`
- **Imports**: Sorted with `isort`
- **Type hints**: Use where helpful
- **Docstrings**: Required for public APIs

### Example

```python
"""Module docstring describing the module."""

from typing import Optional, Dict, Any
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.video_service import VideoService


class VideoRequest(BaseModel):
    """Request model for video operations."""

    url: str
    quality: Optional[str] = "best"


router = APIRouter(prefix="/api/v2/videos", tags=["videos"])


@router.post("/download")
async def download_video(request: VideoRequest) -> Dict[str, Any]:
    """
    Download a video from the specified URL.

    Args:
        request: The video download request

    Returns:
        Dict containing download information

    Raises:
        HTTPException: If the download fails
    """
    try:
        service = VideoService()
        result = await service.download(request.url, request.quality)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Code Quality Commands

```bash
make format      # Format code (black, isort)
make lint        # Lint code (ruff)
make type-check  # Type checking (mypy)
make quality     # All checks
```

---

## 📚 Documentation

### Docstrings

Use **Google style** docstrings:

```python
def process_video(url: str, quality: str = "best") -> VideoInfo:
    """
    Process a video from the given URL.

    This function downloads video metadata and prepares it for streaming.

    Args:
        url: The video URL to process
        quality: The desired video quality (default: "best")

    Returns:
        VideoInfo object containing video metadata

    Raises:
        ValidationError: If the URL is invalid
        VideoNotFoundError: If the video cannot be found

    Example:
        >>> info = process_video("https://youtube.com/watch?v=dQw4w9WgXcQ")
        >>> print(info.title)
        'Rick Astley - Never Gonna Give You Up'
    """
    pass
```

### Code Comments

- **Why, not what**: Explain the reasoning, not the obvious
- **TODOs**: Use `# TODO: description` for future work
- **Complex logic**: Add comments for non-obvious code

```python
# Good: Explains why
# We use exponential backoff to avoid overwhelming the API
await asyncio.sleep(2 ** retry_count)

# Bad: States the obvious
# Sleep for 2 seconds
await asyncio.sleep(2)
```

---

## 🐛 Bug Reports

### Before Submitting

1. Check if the bug has already been reported
2. Try to reproduce on the latest version
3. Gather relevant information

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., macOS 13.0]
- Python version: [e.g., 3.12.0]
- Docker version: [e.g., 24.0.0]

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other relevant information.
```

---

## 💡 Feature Requests

### Before Submitting

1. Check if the feature has been suggested
2. Consider if it fits the project scope
3. Think about implementation details

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Additional context**
Any other relevant information, mockups, or examples.
```

---

## 🔍 Code Review Process

### What We Look For

- ✅ **Functionality**: Does it work as intended?
- ✅ **Tests**: Are there adequate tests?
- ✅ **Code Quality**: Is it clean and maintainable?
- ✅ **Documentation**: Is it properly documented?
- ✅ **Performance**: Is it efficient?
- ✅ **Security**: Are there any security concerns?

### Review Checklist

Before requesting review:

- [ ] All tests pass (`make test-all`)
- [ ] Code quality checks pass (`make quality`)
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] PR description is clear
- [ ] Related issues are referenced

---

## 📋 Pull Request Guidelines

### PR Title

Use conventional commit format:

```
feat: add video quality selection
fix: resolve streaming timeout
docs: update API documentation
test: add integration tests for streaming
```

### PR Description

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- List of changes
- Another change

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots

## Checklist
- [ ] Tests pass
- [ ] Code quality checks pass
- [ ] Documentation updated
- [ ] CHANGELOG updated (for significant changes)

## Related Issues
Closes #123
```

### PR Size

- **Small PRs** are better (< 400 lines)
- **One concern per PR**: Don't mix features and refactoring
- **Split large changes**: Into multiple PRs

---

## 🏷️ Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Adding/updating tests
- **refactor**: Code refactoring
- **style**: Code style changes (formatting)
- **perf**: Performance improvements
- **chore**: Maintenance tasks
- **ci**: CI/CD changes
- **build**: Build system changes

### Examples

```bash
feat: add support for Instagram stories
fix: resolve memory leak in video processing
docs: update installation guide
test: add unit tests for auth service
refactor: simplify error handling logic
perf: optimize video streaming buffer size
chore: update dependencies
ci: add coverage reporting to pipeline
```

### Scope (Optional)

```bash
feat(api): add new streaming endpoint
fix(docker): resolve build issues
docs(readme): update quick start guide
```

---

## 🌳 Branch Strategy

### Main Branches

- `master`: Production-ready code
- `develop`: Development branch (default)

### Feature Branches

```bash
feature/video-quality-selection
feature/instagram-support
fix/streaming-timeout
docs/api-documentation
test/integration-tests
```

### Workflow

```
develop → feature/your-feature → PR → develop → master
```

---

## 🎯 What to Contribute

### Good First Issues

Look for issues labeled:
- `good first issue`
- `help wanted`
- `documentation`
- `beginner friendly`

### Areas to Contribute

- 🐛 **Bug fixes**: Fix reported issues
- ✨ **Features**: Implement new features
- 📚 **Documentation**: Improve docs
- 🧪 **Tests**: Add test coverage
- 🎨 **UI/UX**: Improve user experience
- ⚡ **Performance**: Optimize code
- 🔒 **Security**: Fix security issues

---

## 🤔 Questions?

- 💬 **Discussions**: Use GitHub Discussions for questions
- 📚 **Documentation**: Check the docs first
- 🐛 **Issues**: Create an issue if you find a bug
- 📧 **Email**: Contact maintainers for private matters

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

## 🙏 Thank You!

Every contribution helps make this project better. Thank you for taking the time to contribute! 🎉

---

**Happy Contributing! 🚀**
