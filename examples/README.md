# 📚 Examples & Demos

This directory contains practical examples demonstrating how to use the YouTuberBilBiliHelper API.

---

## 🎯 Available Examples

### 1. Authentication Demo
**File:** `authentication_demo.py`

Demonstrates how to:
- Set up authentication with various platforms
- Manage cookies and sessions
- Handle authentication errors
- Verify authentication status

```bash
python examples/authentication_demo.py
```

---

### 2. Streaming Demo
**File:** `streaming_demo.py`

Demonstrates how to:
- Get direct stream URLs
- Use proxy streaming
- Handle different quality options
- Optimize for different players (VRChat, Unity)

```bash
python examples/streaming_demo.py
```

---

### 3. Benchmark Demo
**File:** `benchmark_demo.py`

Demonstrates how to:
- Run performance benchmarks
- Compare API endpoint speeds
- Measure response times
- Analyze throughput

```bash
python examples/benchmark_demo.py
```

---

## 🚀 Quick Start

### Prerequisites

1. **API Running**: Make sure the API is running
   ```bash
   make dev
   ```

2. **Dependencies**: Ensure you have required packages
   ```bash
   pip install -r requirements-dev.txt
   ```

### Running Examples

Each example can be run independently:

```bash
# Run authentication demo
python examples/authentication_demo.py

# Run streaming demo
python examples/streaming_demo.py

# Run benchmark demo
python examples/benchmark_demo.py
```

---

## 📖 Example Usage

### Basic Video Information

```python
import httpx

# Get video information
response = httpx.get(
    "http://localhost:8000/api/v2/videos/youtube/dQw4w9WgXcQ"
)
video_info = response.json()
print(f"Title: {video_info['title']}")
```

### Streaming Video

```python
import httpx

# Get stream URL
response = httpx.get(
    "http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ",
    params={"quality": "720p"},
    follow_redirects=True
)
# Stream is returned or redirected
```

### Batch Operations

```python
import httpx

# Process multiple videos
response = httpx.post(
    "http://localhost:8000/api/v2/videos/batch",
    json={
        "videos": [
            {"url": "https://youtube.com/watch?v=VIDEO1", "quality": "best"},
            {"url": "https://youtube.com/watch?v=VIDEO2", "quality": "720p"}
        ],
        "parallel": True,
        "max_concurrent": 3
    }
)
batch_result = response.json()
```

---

## 🧪 Testing

**Note:** Test files have been moved to the `tests/` directory for better organization.

- **Unit Tests**: `tests/unit/`
- **Integration Tests**: `tests/integration/`
- **E2E Tests**: `tests/e2e/`

To run all tests:
```bash
make test-all
```

---

## 💡 Best Practices

### 1. Error Handling

Always handle potential errors:

```python
try:
    response = httpx.get("http://localhost:8000/api/v2/videos/...")
    response.raise_for_status()
    data = response.json()
except httpx.HTTPError as e:
    print(f"HTTP error occurred: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
```

### 2. Timeout Configuration

Set appropriate timeouts:

```python
response = httpx.get(
    "http://localhost:8000/api/v2/stream/...",
    timeout=30.0  # 30 second timeout
)
```

### 3. Async Operations

For better performance, use async:

```python
import httpx
import asyncio

async def fetch_video_info(video_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v2/videos/youtube/{video_id}"
        )
        return response.json()

# Run async
asyncio.run(fetch_video_info("dQw4w9WgXcQ"))
```

---

## 🔗 Related Documentation

- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[Getting Started Guide](../docs/getting-started/GETTING_STARTED.md)** - Detailed development guide
- **[Contributing Guide](../docs/development/CONTRIBUTING.md)** - How to contribute

---

## 📝 Creating New Examples

Want to add a new example? Follow these guidelines:

1. **Naming**: Use `*_demo.py` for demonstration scripts
2. **Documentation**: Add clear comments and docstrings
3. **Error Handling**: Include proper error handling
4. **Self-Contained**: Make examples work independently
5. **Update README**: Add your example to this README

### Example Template

```python
"""
Example: [What this demonstrates]

This example shows how to:
- Point 1
- Point 2
- Point 3
"""

import httpx


def main():
    """Main demonstration function."""
    # Setup
    api_base = "http://localhost:8000"
    
    try:
        # Your example code here
        response = httpx.get(f"{api_base}/api/v2/...")
        response.raise_for_status()
        
        # Process results
        data = response.json()
        print(f"Success: {data}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
```

---

## 🆘 Troubleshooting

### API Not Responding

```bash
# Check if API is running
make health

# Restart API
make stop
make dev
```

### Import Errors

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Or use uv
uv pip install -r requirements-dev.txt
```

### Connection Refused

Make sure the API is running on the correct port:
```bash
# Check running services
make status

# View logs
make logs
```

---

## 📊 Performance Tips

1. **Use Async**: For multiple requests, use async operations
2. **Connection Pooling**: Reuse HTTP clients
3. **Caching**: Enable caching for repeated requests
4. **Batch Operations**: Use batch endpoints when available

---

**Last Updated:** October 29, 2025  
**Examples Version:** 2.0  

**Happy Coding! 🚀**
