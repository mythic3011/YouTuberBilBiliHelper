package services

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"video-streaming-api/internal/config"
	"video-streaming-api/internal/models"

	"github.com/sirupsen/logrus"
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

// GetPlaylistInfo retrieves playlist metadata using yt-dlp
func (s *VideoService) GetPlaylistInfo(ctx context.Context, platform, playlistID string) (*models.PlaylistInfo, error) {
	cacheKey := GenerateCacheKey("playlist", platform, playlistID)

	var cachedInfo models.PlaylistInfo
	if err := s.redis.GetJSON(ctx, cacheKey, &cachedInfo); err == nil {
		s.logger.WithFields(logrus.Fields{
			"platform":    platform,
			"playlist_id": playlistID,
		}).Debug("Playlist info cache hit")
		return &cachedInfo, nil
	}

	playlistURL := s.buildVideoURL(platform, playlistID)
	info, err := s.extractPlaylistInfo(ctx, playlistURL)
	if err != nil {
		return nil, fmt.Errorf("failed to extract playlist info: %w", err)
	}

	if err := s.redis.SetJSON(ctx, cacheKey, info, s.cfg.VideoInfoTTL); err != nil {
		s.logger.WithError(err).Warn("Failed to cache playlist info")
	}

	return info, nil
}

// GetStreamURL retrieves a stream URL for a video
func (s *VideoService) GetStreamURL(ctx context.Context, platform, videoID, quality string) (string, error) {
	// Generate cache key
	cacheKey := GenerateCacheKey("stream", platform, videoID, quality)

	// Try cache first
	if cached, err := s.redis.Get(ctx, cacheKey); err == nil {
		if sanitized, err := sanitizeStreamURL(cached); err == nil {
			s.logger.WithFields(logrus.Fields{
				"platform": platform,
				"video_id": videoID,
				"quality":  quality,
			}).Debug("Stream URL cache hit")
			return sanitized, nil
		}

		s.logger.WithError(err).Warn("Cached stream URL invalid, regenerating")
	}

	// Cache miss - get from yt-dlp
	videoURL := s.buildVideoURL(platform, videoID)
	streamURL, err := s.extractStreamURL(ctx, videoURL, quality)
	if err != nil {
		return "", fmt.Errorf("failed to extract stream URL: %w", err)
	}
	streamURL, err = sanitizeStreamURL(streamURL)
	if err != nil {
		return "", err
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
		Platform:    s.DetectPlatform(videoURL),
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

// extractPlaylistInfo calls yt-dlp to extract playlist metadata
func (s *VideoService) extractPlaylistInfo(ctx context.Context, playlistURL string) (*models.PlaylistInfo, error) {
	cmd := exec.CommandContext(ctx, "yt-dlp",
		"--dump-single-json",
		"--flat-playlist",
		"--no-warnings",
		playlistURL,
	)

	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("yt-dlp playlist command failed: %w", err)
	}

	var ytdlpPlaylist struct {
		ID          string `json:"id"`
		Title       string `json:"title"`
		Description string `json:"description"`
		Uploader    string `json:"uploader"`
		WebpageURL  string `json:"webpage_url"`
		Entries     []struct {
			ID         string `json:"id"`
			Title      string `json:"title"`
			Duration   int    `json:"duration"`
			Uploader   string `json:"uploader"`
			WebpageURL string `json:"webpage_url"`
		} `json:"entries"`
	}

	if err := json.Unmarshal(output, &ytdlpPlaylist); err != nil {
		return nil, fmt.Errorf("failed to parse yt-dlp playlist output: %w", err)
	}

	info := &models.PlaylistInfo{
		ID:          ytdlpPlaylist.ID,
		Title:       ytdlpPlaylist.Title,
		Description: ytdlpPlaylist.Description,
		Uploader:    ytdlpPlaylist.Uploader,
		WebpageURL:  ytdlpPlaylist.WebpageURL,
		EntryCount:  len(ytdlpPlaylist.Entries),
		Platform:    s.DetectPlatform(playlistURL),
		Entries:     make([]models.PlaylistEntry, 0, len(ytdlpPlaylist.Entries)),
	}

	for _, entry := range ytdlpPlaylist.Entries {
		info.Entries = append(info.Entries, models.PlaylistEntry{
			ID:         entry.ID,
			Title:      entry.Title,
			Duration:   entry.Duration,
			Uploader:   entry.Uploader,
			WebpageURL: entry.WebpageURL,
		})
	}

	return info, nil
}

// IsPlaylist checks if the given video ID/URL is a playlist
func (s *VideoService) IsPlaylist(ctx context.Context, platform, videoID string) (bool, error) {
	// Generate cache key for playlist detection
	cacheKey := GenerateCacheKey("is_playlist", platform, videoID)

	// Try cache first
	if cached, err := s.redis.Get(ctx, cacheKey); err == nil {
		return strings.EqualFold(cached, "true"), nil
	}

	videoURL := s.buildVideoURL(platform, videoID)

	cmd := exec.CommandContext(ctx, "yt-dlp",
		"--dump-json",
		"--no-warnings",
		videoURL,
	)

	output, err := cmd.Output()
	if err != nil {
		s.logger.WithError(err).WithFields(logrus.Fields{
			"platform": platform,
			"video_id": videoID,
		}).Warn("Failed to detect playlist type")
		return false, fmt.Errorf("yt-dlp command failed: %w", err)
	}

	var ytdlpInfo struct {
		Entries       interface{} `json:"entries"`
		ID            string      `json:"id"`
		_Type         string      `json:"_type"`
		IsPlaylist    bool        `json:"is_playlist"`
	}

	if err := json.Unmarshal(output, &ytdlpInfo); err != nil {
		s.logger.WithError(err).Warn("Failed to parse playlist detection output")
		return false, fmt.Errorf("failed to parse yt-dlp output: %w", err)
	}

	// Determine if it's a playlist based on multiple indicators
	isPlaylist := ytdlpInfo.Entries != nil || ytdlpInfo.IsPlaylist || ytdlpInfo._Type == "playlist"

	// Cache the result with a longer TTL for playlist detection (24 hours)
	result := "false"
	if isPlaylist {
		result = "true"
	}
	if err := s.redis.Set(ctx, cacheKey, result, 24*time.Hour); err != nil {
		s.logger.WithError(err).Debug("Failed to cache playlist detection result")
	}

	s.logger.WithFields(logrus.Fields{
		"platform":    platform,
		"video_id":    videoID,
		"is_playlist": isPlaylist,
	}).Debug("Playlist type detected")

	return isPlaylist, nil
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

	return sanitizeStreamURL(string(output))
}

// sanitizeStreamURL strips whitespace and multi-line entries, returning the first valid URL.
func sanitizeStreamURL(raw string) (string, error) {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return "", fmt.Errorf("no stream URL found")
	}

	for _, line := range strings.Split(trimmed, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		return line, nil
	}

	return "", fmt.Errorf("no stream URL found")
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

// DetectPlatform detects the platform from a URL
func (s *VideoService) DetectPlatform(url string) string {
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
	case "best", "", "auto", "highest":
		return "best[ext=mp4][acodec!=none]/best[acodec!=none]/best"
	case "worst":
		return "worstvideo+worstaudio/worst"
	case "2160p", "4k":
		return "best[height<=2160][acodec!=none]/bestvideo[height<=2160]+bestaudio"
	case "1440p":
		return "best[height<=1440][acodec!=none]/bestvideo[height<=1440]+bestaudio"
	case "1080p", "hd":
		return "best[height<=1080][acodec!=none]/bestvideo[height<=1080]+bestaudio"
	case "720p":
		return "best[height<=720][acodec!=none]/bestvideo[height<=720]+bestaudio"
	case "480p", "sd":
		return "best[height<=480][acodec!=none]/bestvideo[height<=480]+bestaudio"
	case "360p":
		return "best[height<=360][acodec!=none]/bestvideo[height<=360]+bestaudio"
	default:
		return "best[acodec!=none]/bestvideo+bestaudio"
	}
}

// ValidatePlatform checks if a platform is supported
func (s *VideoService) ValidatePlatform(platform string) bool {
	supported := []string{"youtube", "bilibili", "twitter", "x", "instagram", "twitch", "auto"}
	platform = strings.ToLower(platform)
	for _, p := range supported {
		if p == platform {
			return true
		}
	}
	return false
}
