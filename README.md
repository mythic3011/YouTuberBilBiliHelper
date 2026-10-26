# 🚀 Video Streaming API (Go)

Go + Gin video metadata and streaming API using yt-dlp and Redis.

## Runtime notes

The service uses Go, Redis and yt-dlp. Throughput, latency and memory depend on host resources, provider response time and traffic mix; no benchmark figures are claimed without reproducible measurements.

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
docker compose up -d --build

# Test the API
curl http://localhost:8001/health
```

### Option 2: Local Development

```bash
# Prerequisites
# - Go 1.24 or later
# - Redis
# - yt-dlp: uv tool install yt-dlp

# Install dependencies
go mod download

# Run Redis
docker run -d -p 127.0.0.1:6379:6379 redis:7-alpine

# Run the API
go run .

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
VIDEO_INFO_TTL=1h        # Video info cache TTL
STREAM_URL_TTL=5m         # Stream URL cache TTL
```

### Rate Limiting

```bash
RATE_LIMIT_ENABLED=true           # Enable rate limiting
RATE_LIMIT_MAX_REQUESTS=100      # Max requests per window
RATE_LIMIT_WINDOW=60              # Window size (seconds)
```

### Smart Proxy Configuration

```bash
SMART_PROXY_ENABLED=true          # Enable smart proxy routing
PROXY_COUNTRIES=CN                # Countries that use proxy (comma-separated)
DEFAULT_STREAM_MODE=direct        # Default mode: 'proxy' or 'direct'
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

**Input contract:** Supply platform-native video IDs in HTTP path parameters. Full URLs (including slashes and query strings) are not accepted by the public path routes. Auto-detection at the service layer is not equivalent to a working `/auto/https://...` HTTP path.

### Stream Video (Smart Proxy/Direct)

```bash
GET /api/v2/stream/:platform/:video_id?quality=best
```

Automatically routes traffic through proxy for configured countries (default: CN) or serves direct redirects for others. Override with `mode=proxy` or `mode=direct` query parameter.

**Query Parameters:**

- `quality`: Video quality (best, worst, 2160p, 1440p, 1080p, 720p, 480p, 360p)
- `mode`: Force routing mode (proxy, direct, or omit for smart detection)
- `country`: Override detected country for testing (e.g., `country=CN`)

**Example (smart routing):**

```bash
curl "http://localhost:8001/api/v2/stream/youtube/dQw4w9WgXcQ?quality=1080p"
```

**Example (force proxy):**

```bash
curl "http://localhost:8001/api/v2/stream/youtube/dQw4w9WgXcQ?mode=proxy"
```

**Format limitation:** The proxy/direct endpoint requires one muxed audio+video stream URL. Higher-resolution DASH formats that provide video and audio as two URLs need remuxing and are not silently reduced to video-only. Some requested resolutions may be unavailable. The proxy path rejects m3u8 playlists.

### Get Playlist Information

```bash
GET /api/v2/playlists/:platform/:playlist_id
```

**Example (YouTube playlist ID):**

```bash
curl "http://localhost:8001/api/v2/playlists/youtube/PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO"
```

Returns playlist metadata plus the flattened list of entries.

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
- **Bilibili** (bilibili.com; Bilibili video IDs, not b23.tv shortlinks)
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

# Stream video (smart routing)
curl http://localhost:8001/api/v2/stream/youtube/dQw4w9WgXcQ?quality=720p \
     --output video.mp4

# Get playlist info
curl "http://localhost:8001/api/v2/playlists/youtube/PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO"
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

Measurements vary by host and workload. The `wrk` command above tests the health endpoint, not media extraction or streaming throughput.

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t video-api-go:latest .
```

### Run with Docker

Use Docker Compose instead of standalone `docker run` to ensure Redis is available and named volumes are configured for the non-root API user.

### Docker Compose

```bash
# Start all services
docker compose up -d --build

# View logs
docker compose logs -f

# Stop services
docker compose down
```

---

## 🛠️ Development

### Prerequisites

- Go 1.24 or later
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

**Limitations:** Health reports yt-dlp as available without executing it. Streaming metrics are process-local and not a measurement of provider throughput. This API does not remux separate audio/video formats or transcode HLS streams.

## Deployment security

Compose binds the API to `127.0.0.1` by default and keeps Redis off host ports. Named Docker volumes allow UID 1000 to write audit logs and downloads. Before public exposure, configure TLS ingress and enable API keys. The backend uses the immediate TCP peer for IP allow/deny checks and ignores untrusted forwarding headers; enforce real-client policies at a trusted ingress. The Go media downloader checks IP destinations and redirects, but the separate yt-dlp process still needs container egress restrictions for defense in depth. Streaming cache entries may expire before their TTL if a provider's signed media URL expires early.

## Proxy resource limits

Each API process allows at most **32 simultaneous proxy media responses**. Once the limit is reached, proxy requests return HTTP **503** with `Retry-After: 5`; direct CDN redirects are unaffected. Upstream media connections enforce a **45-second idle read timeout** that resets when network data is received, rather than a total streaming deadline. Outbound media connections accept only ports 80 and 443; this may exclude unusual provider CDNs. These settings supplement, rather than replace, per-client rate limiting and ingress/egress controls.

**API key exemption policy:** `API_KEY_EXEMPT_IPS` defaults to an empty list, including for localhost. A reverse proxy using `127.0.0.1` as the TCP peer must not automatically bypass API authentication. If exemptions are necessary for a protected internal deployment, explicitly configure them after reviewing every ingress path.
