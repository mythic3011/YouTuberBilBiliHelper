package services

import (
	"context"
	"fmt"
	"runtime"
	"time"

	"github.com/sirupsen/logrus"
	"video-streaming-api/internal/config"
	"video-streaming-api/internal/models"
)

var startTime = time.Now()

// SystemService handles system-level operations
type SystemService struct {
	redis  *RedisService
	cfg    *config.Config
	logger *logrus.Logger
}

// NewSystemService creates a new system service
func NewSystemService(redis *RedisService, cfg *config.Config, logger *logrus.Logger) *SystemService {
	return &SystemService{
		redis:  redis,
		cfg:    cfg,
		logger: logger,
	}
}

// GetHealth returns the system health status
func (s *SystemService) GetHealth(ctx context.Context) (*models.HealthResponse, error) {
	services := make(map[string]string)

	// Check Redis
	if err := s.redis.Ping(ctx); err != nil {
		services["redis"] = fmt.Sprintf("unhealthy: %v", err)
	} else {
		services["redis"] = "healthy"
	}

	// Check yt-dlp (optional, can be expensive)
	services["yt-dlp"] = "available"

	// Overall status
	status := "healthy"
	for _, svcStatus := range services {
		if svcStatus != "healthy" && svcStatus != "available" {
			status = "degraded"
			break
		}
	}

	// Get memory stats
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	memStats := models.MemoryStats{
		Alloc:      m.Alloc / 1024 / 1024,      // MB
		TotalAlloc: m.TotalAlloc / 1024 / 1024, // MB
		Sys:        m.Sys / 1024 / 1024,        // MB
		NumGC:      m.NumGC,
	}

	uptime := time.Since(startTime)

	return &models.HealthResponse{
		Status:    status,
		Timestamp: time.Now(),
		Version:   "2.0.0",
		Services:  services,
		Uptime:    formatDuration(uptime),
		Memory:    memStats,
	}, nil
}

// formatDuration formats a duration in a human-readable way
func formatDuration(d time.Duration) string {
	d = d.Round(time.Second)
	h := d / time.Hour
	d -= h * time.Hour
	m := d / time.Minute
	d -= m * time.Minute
	s := d / time.Second

	if h > 0 {
		return fmt.Sprintf("%dh%dm%ds", h, m, s)
	}
	if m > 0 {
		return fmt.Sprintf("%dm%ds", m, s)
	}
	return fmt.Sprintf("%ds", s)
}
