# Product Overview

High-performance video streaming API built with Go that delivers video content from multiple platforms with exceptional performance characteristics.

## Core Functionality

- Video metadata extraction from multiple platforms (YouTube, Bilibili, Twitter/X, Instagram, Twitch)
- Video streaming via proxy or direct URL redirection
- Quality selection for video streams (360p to 4K)
- Redis-based caching for performance optimization
- Health monitoring and metrics tracking

## Performance Targets

- 4,000+ requests per second throughput
- ~5ms average response time
- ~30MB memory footprint
- 1000+ simultaneous connections

## Key Dependencies

- yt-dlp: External video extraction tool (must be installed on system)
- Redis: Caching layer for video metadata and stream URLs
- ffmpeg: Video processing (optional)

## API Design

RESTful API with versioned endpoints (v2), Swagger documentation, and standardized JSON responses with success/error patterns.
