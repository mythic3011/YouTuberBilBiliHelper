# Test Suite Documentation

Comprehensive test suite for YouTuberBilBiliHelper API.

## 📁 Structure

```
tests/
├── conftest.py              # Shared pytest fixtures and configuration
├── quick_test.py            # Quick manual test script for development
│
├── unit/                    # Unit tests (isolated, fast)
│   ├── models/              # Data model tests
│   ├── services/            # Service layer tests
│   ├── routes/              # Route handler tests
│   └── utils/               # Utility function tests
│       ├── test_cache.py
│       └── test_validators.py
│
├── integration/             # Integration tests (with external dependencies)
│   ├── test_api_*.py       # API endpoint tests
│   ├── test_bilibili_*.py  # BiliBili platform tests
│   ├── test_streaming_*.py # Streaming functionality tests
│   ├── test_platforms.py   # Multi-platform tests
│   ├── test_vrchat_*.py    # VRChat compatibility tests
│   └── test_unity_*.py     # Unity compatibility tests
│
└── e2e/                     # End-to-end tests (full workflows)
    └── (planned)
```

## 🏃 Running Tests

### All Tests
```bash
pytest tests/
```

### Unit Tests Only (Fast)
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### Specific Test File
```bash
pytest tests/unit/utils/test_validators.py -v
```

### With Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Quick Development Test
```bash
python tests/quick_test.py
```

## 🎯 Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose:** Test individual components in isolation
- **Speed:** Very fast (< 1ms per test)
- **Dependencies:** No external services (mocked)
- **Coverage:** All utility functions, models, core logic

**Examples:**
- `test_validators.py` - Input validation functions
- `test_cache.py` - Cache key generation and serialization
- `test_models.py` - Pydantic model validation

### Integration Tests (`tests/integration/`)
- **Purpose:** Test API endpoints and service integrations
- **Speed:** Medium (10-100ms per test)
- **Dependencies:** Redis, may require external APIs
- **Coverage:** Route handlers, service interactions

**Examples:**
- `test_api_structure.py` - API endpoint structure and responses
- `test_bilibili_concurrent.py` - BiliBili batch downloads
- `test_streaming.py` - Video streaming functionality

### E2E Tests (`tests/e2e/`)
- **Purpose:** Test complete user workflows
- **Speed:** Slow (seconds per test)
- **Dependencies:** Full stack, external services
- **Coverage:** Real-world scenarios

## 📝 Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_something_fast():
    pass

@pytest.mark.integration
def test_something_with_dependencies():
    pass

@pytest.mark.slow
def test_something_time_consuming():
    pass
```

Run specific markers:
```bash
# Only fast unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Integration tests only
pytest -m integration
```

## 🔧 Configuration

### pytest.ini
Located in `pyproject.toml`:
- Test paths
- Coverage settings
- Marker definitions
- Default options

### conftest.py
Shared fixtures:
- `client` - HTTP test client
- `redis_client` - Redis connection
- `mock_services` - Mocked external services

## ✅ Best Practices

### Unit Tests
1. Test one thing at a time
2. Use descriptive test names (`test_validate_url_with_invalid_scheme`)
3. Arrange-Act-Assert pattern
4. Mock external dependencies
5. Fast execution (< 1ms)

### Integration Tests
1. Test API contracts
2. Use realistic data
3. Clean up after tests
4. Test error scenarios
5. Medium execution time (< 100ms)

### Test Coverage Goals
- Unit tests: >90% coverage
- Integration tests: >80% endpoint coverage
- Critical paths: 100% coverage

## 🚀 Quick Test Script

For rapid development testing without pytest:

```bash
# Make sure the API is running
uvicorn app.main:app --reload

# In another terminal, run quick test
python tests/quick_test.py
```

This tests:
- ✅ Health endpoints
- ✅ Authentication
- ✅ Video info retrieval
- ✅ Streaming URLs

## 📊 Coverage Reports

Generate coverage reports:

```bash
# Terminal report
pytest --cov=app --cov-report=term-missing

# HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

## 🐛 Debugging Tests

```bash
# Run with verbose output
pytest -vv

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Run specific test
pytest tests/unit/utils/test_validators.py::TestValidateURL::test_valid_http_url
```

## 🔄 Continuous Integration

Tests run automatically on:
- Every push to `master`, `main`, or `develop`
- Every pull request
- Changes to `app/`, `tests/`, or `pyproject.toml`

See `.github/workflows/python-ci.yml` for CI configuration.

## 📚 Writing New Tests

### Unit Test Template
```python
"""Unit tests for <module_name>."""

import pytest
from app.module import function_to_test


class TestFunctionName:
    """Tests for function_to_test function."""
    
    def test_valid_input(self):
        result = function_to_test("valid")
        assert result == expected
    
    def test_invalid_input(self):
        with pytest.raises(ValueError):
            function_to_test("invalid")
```

### Integration Test Template
```python
"""Integration tests for <feature>."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_endpoint_success():
    response = client.get("/api/endpoint")
    assert response.status_code == 200
    assert "expected_key" in response.json()


def test_endpoint_error():
    response = client.get("/api/endpoint?invalid=true")
    assert response.status_code == 400
    assert "error" in response.json()
```

## 🎓 Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python unittest best practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated:** October 30, 2025  
**Test Count:** 80+ unit tests, 17 integration tests  
**Coverage:** >85%

