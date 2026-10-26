# Quick Start Guide

Get the Video Streaming API running in with a local Docker Compose deployment.

## Prerequisites

- Docker & Docker Compose (recommended)
- OR Go 1.24+ and Redis (for local development)

## Option 1: Docker (Easiest)

```bash
# 1. Start the services
mkdir -p config
docker compose up -d --build

# 2. Test the API
curl http://localhost:8001/health

# 3. Try streaming a video
curl "http://localhost:8001/api/v2/videos/youtube/dQw4w9WgXcQ"
```

The API is bound to http://127.0.0.1:8001 by default; Redis runs in a private Compose network.

## Option 2: Local Development

```bash
# 1. Install dependencies
go mod download

# 2. Start Redis
docker run -d -p 6379:6379 redis:alpine

# 3. Copy environment file
cp .env.example .env

# 4. Run the API
go run .
```

## Common Commands

```bash
# Build the binary
make build

# Run tests
make test

# Run with hot reload
make dev

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Next Steps

- Read the [README.md](README.md) for full documentation
- Check the API endpoints at http://localhost:8001/health
- View Swagger docs at http://localhost:8001/swagger/index.html

## Troubleshooting

**Port already in use?**

```bash
# Override the host port when starting Compose
PORT=8002 docker compose up -d --build
```

**Redis connection failed?**

```bash
# Make sure Redis is running
docker ps | grep redis
```

**Need help?**

- Check the logs: `docker compose logs`
- Open an issue on GitHub

## Streaming limitations

This API uses a single muxed audio+video media URL for direct redirects and proxy streaming; it cannot automatically combine DASH audio and video tracks. Higher resolutions may be unavailable in muxed form. Do not put a full `https://...` URL into an HTTP path parameter: use a platform-native video or playlist ID instead. Before any public deployment, configure TLS ingress, API key authentication and network egress restrictions.
