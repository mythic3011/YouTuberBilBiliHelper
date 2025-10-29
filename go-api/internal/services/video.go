package services

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
	"video-streaming-api/internal/config"
	"video-streaming-api/internal/models"
)

// VideoService handles video operations
type VideoService struct {
	redis  *RedisService
	cfg    *config.Config
	logger *logrus.Logger
}

// NewVideoService creates a new video service
func NewVideoService(redis *RedisService, cfg *config.Config, logger *logrus.Logger) *VideoService {
	return &VideoService{
		redis:  redis,
		cfg:    cfg,
		logger: logger,
	}
}

// GetVideoInfo retrieves video information using yt-dlp
func (s *VideoService) GetVideoInfo(ctx context.Context, platform, videoID string) (*models.VideoInfo, error) {
	// Generate cache key
	cacheKey := GenerateCacheKey("video", platform, videoID)

	// Try cache first
	var cachedInfo models.VideoInfo
	if err := s.redis.GetJSON(ctx, cacheKey, &cachedInfo); err == nil {
		s.logger.WithFields(logrus.Fields{
			"platform": platform,
			"video_id": videoID,
		}).Debug("Video info cache hit")
		return &cachedInfo, nil
	}

	// Cache miss - fetch from yt-dlp
	s.logger.WithFields(logrus.Fields{
		"platform": platform,
		"video_id": videoID,
	}).Info("Fetching video info from yt-dlp")

	videoURL := s.buildVideoURL(platform, videoID)
	info, err := s.extractVideoInfo(ctx, videoURL)
	if err != nil {
		return nil, fmt.Errorf("failed to extract video info: %w", err)
	}

	// Cache the result
	if err := s.redis.SetJSON(ctx, cacheKey, info, s.cfg.VideoInfoTTL); err != nil {
		s.logger.WithError(err).Warn("Failed to cache video info")
	}

	return info, nil
}

// GetStreamURL retrieves a stream URL for a video
func (s *VideoService) GetStreamURL(ctx context.Context, platform, videoID, quality string) (string, error) {
	// Generate cache key
	cacheKey := GenerateCacheKey("stream", platform, videoID, quality)

	// Try cache first
	if url, err := s.redis.Get(ctx, cacheKey); err == nil {
		s.logger.WithFields(logrus.Fields{
			"platform": platform,
			"video_id": videoID,
			"quality":  quality,
		}).Debug("Stream URL cache hit")
		return url, nil
	}

	// Cache miss - get from yt-dlp
	videoURL := s.buildVideoURL(platform, videoID)
	streamURL, err := s.extractStreamURL(ctx, videoURL, quality)
	if err != nil {
		return "", fmt.Errorf("failed to extract stream URL: %w", err)
	}

	// Cache the result
	if err := s.redis.Set(ctx, cacheKey, streamURL, s.cfg.StreamURLTTL); err != nil {
		s.logger.WithError(err).Warn("Failed to cache stream URL")
	}

	return streamURL, nil
}

// extractVideoInfo calls yt-dlp to extract video information
func (s *VideoService) extractVideoInfo(ctx context.Context, videoURL string) (*models.VideoInfo, error) {
	cmd := exec.CommandContext(ctx, "yt-dlp",
		"--dump-json",
		"--no-playlist",
		"--no-warnings",
		videoURL,
	)

	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("yt-dlp command failed: %w", err)
	}

	// Parse yt-dlp JSON output
	var ytdlpInfo struct {
		ID          string `json:"id"`
		Title       string `json:"title"`
		Description string `json:"description"`
		Duration    int    `json:"duration"`
		Thumbnail   string `json:"thumbnail"`
		Uploader    string `json:"uploader"`
		ViewCount   int64  `json:"view_count"`
		LikeCount   int64  `json:"like_count"`
		UploadDate  string `json:"upload_date"`
		Formats     []struct {
			FormatID   string `json:"format_id"`
			URL        string `json:"url"`
			Ext        string `json:"ext"`
			Resolution string `json:"resolution"`
			Filesize   int64  `json:"filesize"`
			Vcodec     string `json:"vcodec"`
			Acodec     string `json:"acodec"`
		} `json:"formats"`
	}

	if err := json.Unmarshal(output, &ytdlpInfo); err != nil {
		return nil, fmt.Errorf("failed to parse yt-dlp output: %w", err)
	}

	// Convert to our model
	info := &models.VideoInfo{
		ID:          ytdlpInfo.ID,
		Title:       ytdlpInfo.Title,
		Description: ytdlpInfo.Description,
		Duration:    ytdlpInfo.Duration,
		Thumbnail:   ytdlpInfo.Thumbnail,
		Uploader:    ytdlpInfo.Uploader,
		ViewCount:   ytdlpInfo.ViewCount,
		LikeCount:   ytdlpInfo.LikeCount,
		UploadDate:  ytdlpInfo.UploadDate,
		Platform:    s.detectPlatform(videoURL),
		Formats:     make([]models.Format, 0),
	}

	// Convert formats
	for _, f := range ytdlpInfo.Formats {
		if f.URL != "" {
			info.Formats = append(info.Formats, models.Format{
				FormatID:   f.FormatID,
				URL:        f.URL,
				Extension:  f.Ext,
				Resolution: f.Resolution,
				Filesize:   f.Filesize,
				Codec:      f.Vcodec,
			})
		}
	}

	return info, nil
}

// extractStreamURL gets the best stream URL for a given quality
func (s *VideoService) extractStreamURL(ctx context.Context, videoURL, quality string) (string, error) {
	formatSelector := s.getFormatSelector(quality)

	cmd := exec.CommandContext(ctx, "yt-dlp",
		"--get-url",
		"-f", formatSelector,
		"--no-playlist",
		"--no-warnings",
		videoURL,
	)

	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("yt-dlp command failed: %w", err)
	}

	streamURL := strings.TrimSpace(string(output))
	if streamURL == "" {
		return "", fmt.Errorf("no stream URL found")
	}

	return streamURL, nil
}

// buildVideoURL constructs a video URL from platform and ID
func (s *VideoService) buildVideoURL(platform, videoID string) string {
	switch strings.ToLower(platform) {
	case "youtube":
		return fmt.Sprintf("https://www.youtube.com/watch?v=%s", videoID)
	case "bilibili":
		return fmt.Sprintf("https://www.bilibili.com/video/%s", videoID)
	case "twitter", "x":
		return fmt.Sprintf("https://twitter.com/i/status/%s", videoID)
	case "instagram":
		return fmt.Sprintf("https://www.instagram.com/p/%s", videoID)
	case "twitch":
		return fmt.Sprintf("https://www.twitch.tv/videos/%s", videoID)
	default:
		// Assume videoID is a full URL
		return videoID
	}
}

// detectPlatform detects the platform from a URL
func (s *VideoService) detectPlatform(url string) string {
	url = strings.ToLower(url)
	switch {
	case strings.Contains(url, "youtube.com") || strings.Contains(url, "youtu.be"):
		return "youtube"
	case strings.Contains(url, "bilibili.com") || strings.Contains(url, "b23.tv"):
		return "bilibili"
	case strings.Contains(url, "twitter.com") || strings.Contains(url, "x.com"):
		return "twitter"
	case strings.Contains(url, "instagram.com"):
		return "instagram"
	case strings.Contains(url, "twitch.tv"):
		return "twitch"
	default:
		return "unknown"
	}
}

// getFormatSelector returns the yt-dlp format selector for a quality
func (s *VideoService) getFormatSelector(quality string) string {
	switch strings.ToLower(quality) {
	case "best", "":
		return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
	case "worst":
		return "worstvideo+worstaudio/worst"
	case "2160p", "4k":
		return "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
	case "1440p":
		return "bestvideo[height<=1440]+bestaudio/best[height<=1440]"
	case "1080p", "hd":
		return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
	case "720p":
		return "bestvideo[height<=720]+bestaudio/best[height<=720]"
	case "480p", "sd":
		return "bestvideo[height<=480]+bestaudio/best[height<=480]"
	case "360p":
		return "bestvideo[height<=360]+bestaudio/best[height<=360]"
	default:
		return "bestvideo+bestaudio/best"
	}
}

// ValidatePlatform checks if a platform is supported
func (s *VideoService) ValidatePlatform(platform string) bool {
	supported := []string{"youtube", "bilibili", "twitter", "x", "instagram", "twitch"}
	platform = strings.ToLower(platform)
	for _, p := range supported {
		if p == platform {
			return true
		}
	}
	return false
}

