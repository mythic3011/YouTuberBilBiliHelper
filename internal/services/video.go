package services

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
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
	videoURL, err := canonicalMediaURL(platform, videoID, false)
	if err != nil {
		return nil, err
	}
	// Generate cache key from the canonical, validated URL.
	cacheKey := GenerateCacheKey("video", videoURL)

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
	playlistURL, err := canonicalMediaURL(platform, playlistID, true)
	if err != nil {
		return nil, err
	}
	cacheKey := GenerateCacheKey("playlist", playlistURL)

	var cachedInfo models.PlaylistInfo
	if err := s.redis.GetJSON(ctx, cacheKey, &cachedInfo); err == nil {
		s.logger.WithFields(logrus.Fields{
			"platform":    platform,
			"playlist_id": playlistID,
		}).Debug("Playlist info cache hit")
		return &cachedInfo, nil
	}

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
	videoURL, err := canonicalMediaURL(platform, videoID, false)
	if err != nil {
		return "", err
	}
	// Generate cache key from validated, canonical input.
	cacheKey := GenerateCacheKey("stream_muxed_v2", videoURL, quality)

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
	args := []string{
		"--dump-json",
		"--no-playlist",
		"--ignore-config",
		"--socket-timeout", "30",
		"--",
		videoURL,
	}

	s.logger.WithFields(logrus.Fields{
		"video_url": videoURL,
	}).Debug("Fetching video info with yt-dlp")

	output, err := s.runYtDLP(ctx, args)
	if err != nil {
		outputStr := strings.TrimSpace(string(output))
		s.logger.WithFields(logrus.Fields{
			"video_url": videoURL,
			"output":    outputStr,
			"error":     err.Error(),
		}).Error("yt-dlp command failed for video info")
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
	args := []string{
		"--dump-single-json",
		"--flat-playlist",
		"--ignore-config",
		"--socket-timeout", "30",
		"--",
		playlistURL,
	}

	s.logger.WithFields(logrus.Fields{
		"playlist_url": playlistURL,
	}).Debug("Fetching playlist info with yt-dlp")

	output, err := s.runYtDLP(ctx, args)
	if err != nil {
		outputStr := strings.TrimSpace(string(output))
		s.logger.WithFields(logrus.Fields{
			"playlist_url": playlistURL,
			"output":       outputStr,
			"error":        err.Error(),
		}).Error("yt-dlp command failed for playlist info")
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
	videoURL, err := canonicalMediaURL(platform, videoID, false)
	if err != nil {
		return false, err
	}
	// Generate cache key for playlist detection
	cacheKey := GenerateCacheKey("is_playlist", videoURL)

	// Try cache first
	if cached, err := s.redis.Get(ctx, cacheKey); err == nil {
		return strings.EqualFold(cached, "true"), nil
	}

	args := []string{
		"--dump-json",
		"--ignore-config",
		"--socket-timeout", "30",
		"--",
		videoURL,
	}

	output, err := s.runYtDLP(ctx, args)
	if err != nil {
		outputStr := strings.TrimSpace(string(output))
		s.logger.WithFields(logrus.Fields{
			"platform":   platform,
			"video_id":   videoID,
			"video_url":  videoURL,
			"output":     outputStr,
			"error":      err.Error(),
		}).Warn("Failed to detect playlist type")
		return false, fmt.Errorf("yt-dlp command failed: %w", err)
	}

	var ytdlpInfo struct {
		Entries       interface{} `json:"entries"`
		ID            string      `json:"id"`
		Type          string      `json:"_type"`
		IsPlaylist    bool        `json:"is_playlist"`
	}

	if err := json.Unmarshal(output, &ytdlpInfo); err != nil {
		s.logger.WithError(err).Warn("Failed to parse playlist detection output")
		return false, fmt.Errorf("failed to parse yt-dlp output: %w", err)
	}

	// Determine if it's a playlist based on multiple indicators
	isPlaylist := ytdlpInfo.Entries != nil || ytdlpInfo.IsPlaylist || ytdlpInfo.Type == "playlist"

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

	// Build command with enhanced quality flags
	args := []string{
		"--get-url",
		"--no-warnings",
		"-f", formatSelector,
		"--no-playlist",
		"--ignore-config",
		"--socket-timeout", "30",
		"--extractor-args", "youtube:player_client=ios,web,android",
		"--prefer-free-formats",
	}

	args = append(args, "--", videoURL)

	s.logger.WithFields(logrus.Fields{
		"video_url": videoURL,
		"quality":   quality,
	}).Debug("Executing yt-dlp command for stream URL")

	output, err := s.runYtDLP(ctx, args)
	outputStr := strings.TrimSpace(string(output))

	if err != nil {
		// stdout may contain expiring signed URLs, never log or reflect it.
		s.logger.WithFields(logrus.Fields{
			"platform": s.DetectPlatform(videoURL),
			"quality": quality,
		}).WithError(err).Error("yt-dlp stream extraction failed")
		return "", fmt.Errorf("yt-dlp stream extraction failed: %w", err)
	}

	if outputStr == "" {
		s.logger.WithFields(logrus.Fields{
			"video_url": videoURL,
			"quality":   quality,
		}).Warn("yt-dlp returned empty output")
		return "", fmt.Errorf("yt-dlp returned empty URL")
	}

	return sanitizeStreamURL(outputStr)
}

// sanitizeStreamURL requires exactly one usable stream. yt-dlp can emit
// multiple URLs for video+audio formats; selecting only the first silently
// produces video without audio, so reject ambiguous outputs.
func sanitizeStreamURL(raw string) (string, error) {
	var streamURL string
	for _, line := range strings.Split(raw, "\n") {
		candidate := strings.TrimSpace(line)
		if candidate == "" || validateStreamURL(candidate) != nil {
			continue
		}
		if streamURL != "" {
			return "", fmt.Errorf("yt-dlp returned multiple media URLs; remuxing is required")
		}
		streamURL = candidate
	}
	if streamURL == "" {
		return "", fmt.Errorf("yt-dlp returned no valid public HTTP(S) stream URL")
	}
	return streamURL, nil
}

// DetectPlatform determines the provider for a canonical media URL.
func (s *VideoService) DetectPlatform(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil {
		return "unknown"
	}
	switch strings.ToLower(u.Hostname()) {
	case "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be":
		return "youtube"
	case "bilibili.com", "www.bilibili.com":
		return "bilibili"
	case "twitter.com", "www.twitter.com", "x.com", "www.x.com":
		return "twitter"
	case "instagram.com", "www.instagram.com":
		return "instagram"
	case "twitch.tv", "www.twitch.tv":
		return "twitch"
	default:
		return "unknown"
	}
}

// getFormatSelector selects a single muxed video+audio URL.
// A separate bestvideo+bestaudio selection emits two URLs, which a raw
// 302 redirect or byte proxy cannot combine. Higher resolutions that only
// offer DASH tracks require a future server-side muxing implementation.
func (s *VideoService) getFormatSelector(quality string) string {
	switch strings.ToLower(quality) {
	case "best", "", "auto", "highest":
		return "best"
	case "worst":
		return "worst"
	case "2160p", "4k":
		return "best[ext=mp4][height<=2160]/best[height<=2160]"
	case "1440p":
		return "best[ext=mp4][height<=1440]/best[height<=1440]"
	case "1080p", "hd":
		return "best[ext=mp4][height<=1080]/best[height<=1080]"
	case "720p":
		return "best[ext=mp4][height<=720]/best[height<=720]"
	case "480p", "sd":
		return "best[ext=mp4][height<=480]/best[height<=480]"
	case "360p":
		return "best[ext=mp4][height<=360]/best[height<=360]"
	default:
		return "best"
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
