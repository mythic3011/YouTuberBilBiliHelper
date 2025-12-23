# 🚀 Video Streaming API (Go)

High-performance video streaming API built with Go, delivering exceptional performance for video content management across multiple platforms.

## ⚡ Performance Highlights

- **Throughput**: 4,000+ requests per second
- **Latency**: ~5ms average response time
- **Memory**: ~30MB footprint
- **Concurrency**: Handles 1000+ simultaneous connections

---

## 📁 Project Structure

```
.
├── main.go                    # Application entry point
├── go.mod                     # Go dependencies
├── go.sum                     # Dependency checksums
├── Dockerfile                 # Production Docker image
├── docker-compose.yml         # Docker orchestration
├── .air.toml                  # Hot reload configuration
├── internal/
│   ├── config/               # Configuration management
│   ├── models/               # Data models
│   ├── services/             # Business logic
│   │   ├── redis.go         # Redis service
│   │   ├── video.go         # Video service
│   │   ├── streaming.go     # Streaming service
│   │   └── system.go        # System service
│   └── api/                  # HTTP handlers
│       ├── handlers.go      # Request handlers
│       ├── routes.go        # Route definitions
│       └── middleware.go    # HTTP middleware
├── docs/                      # Swagger documentation
└── tmp/                       # Build artifacts
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Test the API
curl http://localhost:8001/health
```

### Option 2: Local Development

```bash
# Prerequisites
# - Go 1.21 or later
# - Redis
# - yt-dlp: pip3 install yt-dlp

# Install dependencies
go mod download

# Run Redis
docker run -d -p 6379:6379 redis:alpine

# Run the API
go run main.go

# Or build and run
go build -o video-api
./video-api
```

### Option 3: Hot Reload Development

```bash
# Install air for hot reload
go install github.com/cosmtrek/air@latest

# Run with hot reload
air
```

---

## 📚 API Documentation

- The OpenAPI/Swagger docs are generated from inline annotations (similar to how JSDoc extracts comments). No manual JSON editing is required.
- Docker builds now install the `swag` CLI and run `swag init` automatically, so containers always embed the latest spec.
- For local development (if you want to preview docs without rebuilding Docker), you can still run `swag init -g main.go -o docs`, but this is optional.
- Commit the refreshed `docs/` output if you regenerate locally so everyone stays in sync.

---

## 🔧 Configuration

Configuration via environment variables:

### Server Configuration

```bash
PORT=8001                    # Server port
ENVIRONMENT=production       # Environment (development/production)
LOG_LEVEL=info              # Log level (debug/info/warn/error)
```

### Redis Configuration

```bash
REDIS_HOST=localhost        # Redis host
REDIS_PORT=6379            # Redis port
REDIS_PASSWORD=            # Redis password (optional)
REDIS_DB=0                 # Redis database number
```

### Cache Configuration

```bash
CACHE_TTL=300              # General cache TTL (seconds)
VIDEO_INFO_TTL=3600        # Video info cache TTL
STREAM_URL_TTL=600         # Stream URL cache TTL
AUTH_STATUS_TTL=1800       # Auth status cache TTL
```

### Rate Limiting

```bash
RATE_LIMIT_ENABLED=true           # Enable rate limiting
RATE_LIMIT_MAX_REQUESTS=1000      # Max requests per window
RATE_LIMIT_WINDOW=60              # Window size (seconds)
```

---

## 📖 API Endpoints

### Health Check

```bash
GET /health
GET /api/v2/system/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-12-06T22:00:00Z",
  "version": "2.0.0",
  "services": {
    "redis": "healthy",
    "yt-dlp": "available"
  },
  "uptime": "1h30m45s",
  "memory": {
    "alloc_mb": 25,
    "total_alloc_mb": 150,
    "sys_mb": 35,
    "num_gc": 12
  }
}
```

### Get Video Information

```bash
GET /api/v2/videos/:platform/:video_id
```

**Example:**

```bash
curl http://localhost:8001/api/v2/videos/youtube/dQw4w9WgXcQ
```

> **Tip:** If you don't know the platform ahead of time, send the full video URL in place of `:video_id`; the service will auto-detect the platform internally.

**Example (auto-detect platform):**

```bash
curl "http://localhost:8001/api/v2/videos/auto/https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Stream Video (Proxy)

```bash
GET /api/v2/stream/proxy/:platform/:video_id?quality=720p
```

**Example:**

```bash
curl http://localhost:8001/api/v2/stream/proxy/youtube/dQw4w9WgXcQ?quality=1080p
```

> **Tip:** You can also pass the full video URL with `auto` to let the API detect the platform on the fly.

**Example (auto-detect platform):**

```bash
curl "http://localhost:8001/api/v2/stream/proxy/auto/https://music.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Get Playlist Information

```bash
GET /api/v2/playlists/:platform/:playlist_id
```

**Example:**

```bash
curl "http://localhost:8001/api/v2/playlists/auto/https://music.youtube.com/playlist?list=PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO&si=zEWAaTAaQ5iHM-X3"
```

Returns playlist metadata plus the flattened list of entries.

### Get Direct Stream URL

```bash
GET /api/v2/stream/direct/:platform/:video_id?quality=720p
```

Returns a 302 redirect to the actual stream URL.

### Get Streaming Metrics

```bash
GET /api/v2/stream/metrics
```

**Response:**

```json
{
  "success": true,
  "message": "Streaming metrics retrieved successfully",
  "data": {
    "total_requests": 15420,
    "cache_hits": 14235,
    "cache_misses": 1185,
    "cache_hit_rate": 92.3,
    "total_bytes_served": 5368709120,
    "active_streams": 23
  }
}
```

---

## 🎯 Supported Platforms

- **YouTube** (youtube.com, youtu.be)
- **Bilibili** (bilibili.com, b23.tv)
- **Twitter/X** (twitter.com, x.com)
- **Instagram** (instagram.com)
- **Twitch** (twitch.tv)

---

## 🧪 Testing

### Manual Testing

```bash
# Health check
curl http://localhost:8001/health

# Get video info
curl http://localhost:8001/api/v2/videos/youtube/dQw4w9WgXcQ

# Stream video
curl http://localhost:8001/api/v2/stream/proxy/youtube/dQw4w9WgXcQ?quality=720p \
     --output video.mp4
```

### Performance Testing

```bash
# Install wrk (load testing tool)
# macOS
brew install wrk

# Linux
sudo apt-get install wrk

# Run load test
wrk -t12 -c400 -d30s http://localhost:8001/health
```

**Expected Results:**

- Requests/sec: 4,000-6,000
- Latency: 1-5ms average
- Memory: < 50MB

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t video-api-go:latest .
```

### Run with Docker

```bash
docker run -d \
  -p 8001:8001 \
  -e REDIS_HOST=host.docker.internal \
  --name video-api-go \
  video-api-go:latest
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 🛠️ Development

### Prerequisites

- Go 1.21 or later
- Redis
- yt-dlp
- ffmpeg (for video processing)

### Setup Development Environment

```bash
# Install dependencies
go mod download

# Run tests
go test ./...

# Run with hot reload
go install github.com/cosmtrek/air@latest
air
```

### Code Organization

- `main.go` - Application entry point and setup
- `internal/config` - Configuration management
- `internal/models` - Data structures
- `internal/services` - Business logic layer
- `internal/api` - HTTP handling layer

### Adding New Features

1. Add models in `internal/models/`
2. Implement business logic in `internal/services/`
3. Add HTTP handlers in `internal/api/handlers.go`
4. Register routes in `internal/api/routes.go`

---

## 📝 License

MIT License

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/mythic3011/YouTuberBilBiliHelper/issues)

---

**Built with Go 🚀 for maximum performance!**

Last Updated: December 6, 2025
