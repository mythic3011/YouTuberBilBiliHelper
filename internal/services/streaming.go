package services

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	"video-streaming-api/internal/config"
	"video-streaming-api/internal/models"
)

// StreamingService handles video streaming operations
type StreamingService struct {
	video  *VideoService
	redis  *RedisService
	cfg    *config.Config
	logger *logrus.Logger

	// Metrics
	totalRequests    int64
	cacheHits        int64
	cacheMisses      int64
	totalBytesServed int64
	activeStreams    int32
}

// NewStreamingService creates a new streaming service
func NewStreamingService(video *VideoService, redis *RedisService, cfg *config.Config, logger *logrus.Logger) *StreamingService {
	return &StreamingService{
		video:  video,
		redis:  redis,
		cfg:    cfg,
		logger: logger,
	}
}

// StreamVideo streams a video through the proxy
func (s *StreamingService) StreamVideo(c *gin.Context, platform, videoID, quality string) error {
	atomic.AddInt64(&s.totalRequests, 1)
	atomic.AddInt32(&s.activeStreams, 1)
	defer atomic.AddInt32(&s.activeStreams, -1)

	startTime := time.Now()

	// Get stream URL
	streamURL, err := s.video.GetStreamURL(c.Request.Context(), platform, videoID, quality)
	if err != nil {
		atomic.AddInt64(&s.cacheMisses, 1)
		return fmt.Errorf("failed to get stream URL: %w", err)
	}

	atomic.AddInt64(&s.cacheHits, 1)

	// Fetch the video stream
	req, err := http.NewRequestWithContext(c.Request.Context(), "GET", streamURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Copy headers from original request
	for key, values := range c.Request.Header {
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}

	// Execute request
	client := &http.Client{
		Timeout: 30 * time.Second,
	}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to fetch stream: %w", err)
	}
	defer resp.Body.Close()

	// Copy response headers
	for key, values := range resp.Header {
		for _, value := range values {
			c.Header(key, value)
		}
	}

	// Set additional headers
	c.Header("X-Proxy-Server", "Go-Streaming-API")
	c.Header("X-Platform", platform)
	c.Header("X-Quality", quality)

	// Stream the content
	c.Status(resp.StatusCode)

	bytesWritten, err := io.Copy(c.Writer, resp.Body)
	if err != nil {
		s.logger.WithError(err).Warn("Error streaming video")
		return err
	}

	atomic.AddInt64(&s.totalBytesServed, bytesWritten)

	s.logger.WithFields(logrus.Fields{
		"platform":    platform,
		"video_id":    videoID,
		"quality":     quality,
		"bytes":       bytesWritten,
		"duration_ms": time.Since(startTime).Milliseconds(),
	}).Info("Video streamed successfully")

	return nil
}

// GetDirectStreamURL returns a redirect to the direct stream URL
func (s *StreamingService) GetDirectStreamURL(ctx context.Context, platform, videoID, quality string) (string, error) {
	atomic.AddInt64(&s.totalRequests, 1)

	streamURL, err := s.video.GetStreamURL(ctx, platform, videoID, quality)
	if err != nil {
		atomic.AddInt64(&s.cacheMisses, 1)
		return "", fmt.Errorf("failed to get stream URL: %w", err)
	}

	atomic.AddInt64(&s.cacheHits, 1)
	return streamURL, nil
}

// GetMetrics returns streaming performance metrics
func (s *StreamingService) GetMetrics() *models.StreamMetrics {
	totalReq := atomic.LoadInt64(&s.totalRequests)
	hits := atomic.LoadInt64(&s.cacheHits)
	misses := atomic.LoadInt64(&s.cacheMisses)

	hitRate := 0.0
	if totalReq > 0 {
		hitRate = float64(hits) / float64(totalReq) * 100
	}

	return &models.StreamMetrics{
		TotalRequests:    totalReq,
		CacheHits:        hits,
		CacheMisses:      misses,
		CacheHitRate:     hitRate,
		TotalBytesServed: atomic.LoadInt64(&s.totalBytesServed),
		ActiveStreams:    int(atomic.LoadInt32(&s.activeStreams)),
	}
}

// ResetMetrics resets all metrics (useful for testing)
func (s *StreamingService) ResetMetrics() {
	atomic.StoreInt64(&s.totalRequests, 0)
	atomic.StoreInt64(&s.cacheHits, 0)
	atomic.StoreInt64(&s.cacheMisses, 0)
	atomic.StoreInt64(&s.totalBytesServed, 0)
	atomic.StoreInt32(&s.activeStreams, 0)
}
