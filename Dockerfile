# Multi-stage build for optimal size and security

# Build stage
FROM golang:1.24-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Install swagger generator so docs are rebuilt automatically during image builds
RUN go install github.com/swaggo/swag/cmd/swag@latest

# Copy go mod files first for better layer caching
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Tidy and verify modules after source is available
RUN go mod tidy && go mod verify

# Regenerate Swagger docs from inline annotations (mirrors how JS doc generators work)
RUN swag init -g main.go -o docs

# Build the application with optimizations
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -a -installsuffix cgo \
    -ldflags="-w -s -X main.Version=$(git describe --tags --always --dirty 2>/dev/null || echo 'dev')" \
    -o video-api \
    .

# Final stage - minimal runtime image
FROM alpine:3.19

# Install runtime dependencies in a single layer
RUN apk --no-cache add \
    ca-certificates \
    python3 \
    py3-pip \
    ffmpeg \
    curl \
    tzdata \
    nodejs \
    && pip3 install --no-cache-dir --break-system-packages yt-dlp[default] \
    && rm -rf /var/cache/apk/* /tmp/* /root/.cache

# Copy timezone data from builder
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Create app user with specific UID/GID for consistency
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

WORKDIR /app

# Copy binary from builder with correct name
COPY --from=builder /build/video-api .

# Create necessary directories with proper permissions
RUN mkdir -p \
    downloads/youtube \
    downloads/bilibili \
    downloads/twitter \
    downloads/instagram \
    downloads/twitch \
    downloads/temp \
    logs \
    config/cookies \
    && chown -R appuser:appuser /app

# Switch to non-root user for security
USER appuser

# Expose application port
EXPOSE 8001

# Health check with proper endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/api/v2/system/health || exit 1

# Run the application
CMD ["./video-api"]
