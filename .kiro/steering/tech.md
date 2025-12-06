# Technology Stack

## Language & Runtime

- Go 1.24.0
- Standard library with minimal external dependencies

## Core Frameworks & Libraries

- **Gin**: HTTP web framework for routing and middleware
- **go-redis/v9**: Redis client for caching
- **logrus**: Structured logging
- **swaggo/swag**: Swagger/OpenAPI documentation generation

## External Tools

- **yt-dlp**: Video extraction (system dependency, not Go package)
- **ffmpeg**: Video processing (optional system dependency)

## Development Tools

- **air**: Hot reload for development
- **Docker & Docker Compose**: Containerization and orchestration
- **golangci-lint**: Linting (optional)
- **goimports**: Import formatting (optional)

## Build System

### Common Commands

```bash
# Development
make run              # Run application directly
make dev              # Run with hot reload (requires air)
go run main.go        # Alternative direct run

# Building
make build            # Build binary to ./video-api
go build -o video-api # Alternative build

# Testing
make test             # Run tests with race detection and coverage
make test-coverage    # Generate HTML coverage report
go test ./...         # Alternative test command

# Code Quality
make fmt              # Format code
make lint             # Run linters
make vet              # Run go vet

# Docker
make docker-build     # Build Docker image
make docker-up        # Start with docker-compose
make docker-down      # Stop docker-compose
make docker-logs      # View logs

# Dependencies
make deps             # Download dependencies
make tidy             # Tidy go.mod

# Cleanup
make clean            # Remove build artifacts
```

### Quick Start

```bash
# Local development (requires Redis and yt-dlp)
go mod download
go run main.go

# Docker (recommended)
docker-compose up --build
```

## Configuration

Environment variable based configuration (see internal/config/config.go). No config files - all settings via ENV vars with sensible defaults.
