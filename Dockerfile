FROM golang:1.24-alpine AS builder
WORKDIR /build
RUN apk add --no-cache git ca-certificates tzdata
# Align the docs generator with the version declared in go.mod.
RUN go install github.com/swaggo/swag/cmd/swag@v1.16.6
COPY go.mod go.sum ./
RUN go mod download && go mod verify
COPY . .
RUN swag init -g main.go -o docs
# Respect the builder's native architecture (Docker Buildx supports arm64/amd64).
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-w -s" -o /video-api .

FROM alpine:3.24
RUN apk add --no-cache ca-certificates python3 py3-pip ffmpeg curl tzdata nodejs \
    && pip3 install --no-cache-dir --break-system-packages 'yt-dlp[default]'
RUN addgroup -g 1000 appuser && adduser -D -u 1000 -G appuser appuser
WORKDIR /app
COPY --from=builder /video-api /app/video-api
RUN mkdir -p downloads/youtube downloads/bilibili downloads/twitter \
    downloads/instagram downloads/twitch downloads/temp logs config/cookies \
    && chown -R appuser:appuser /app
COPY --chmod=755 healthcheck.sh /app/healthcheck.sh
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/app/healthcheck.sh"]
CMD ["/app/video-api"]
