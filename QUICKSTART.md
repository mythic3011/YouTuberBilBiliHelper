# Quick Start Guide

Get the Video Streaming API running in under 5 minutes!

## Prerequisites

- Docker & Docker Compose (recommended)
- OR Go 1.21+ and Redis (for local development)

## Option 1: Docker (Easiest)

```bash
# 1. Start the services
docker-compose up -d

# 2. Test the API
curl http://localhost:8001/health

# 3. Try streaming a video
curl "http://localhost:8001/api/v2/videos/youtube/dQw4w9WgXcQ"
```

That's it! The API is running at http://localhost:8001

## Option 2: Local Development

```bash
# 1. Install dependencies
go mod download

# 2. Start Redis
docker run -d -p 6379:6379 redis:alpine

# 3. Copy environment file
cp .env.example .env

# 4. Run the API
go run main.go
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
docker-compose logs -f

# Stop services
docker-compose down
```

## Next Steps

- Read the [README.md](README.md) for full documentation
- Check the API endpoints at http://localhost:8001/health
- View Swagger docs at http://localhost:8001/swagger/index.html

## Troubleshooting

**Port already in use?**

```bash
# Change the port in docker-compose.yml or .env
PORT=8002
```

**Redis connection failed?**

```bash
# Make sure Redis is running
docker ps | grep redis
```

**Need help?**

- Check the logs: `docker-compose logs`
- Open an issue on GitHub
