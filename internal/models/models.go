package models

import "time"

// VideoInfo represents video metadata
type VideoInfo struct {
	ID          string   `json:"id"`
	Title       string   `json:"title"`
	Description string   `json:"description,omitempty"`
	Duration    int      `json:"duration"`
	Thumbnail   string   `json:"thumbnail"`
	Platform    string   `json:"platform"`
	Uploader    string   `json:"uploader,omitempty"`
	ViewCount   int64    `json:"view_count,omitempty"`
	LikeCount   int64    `json:"like_count,omitempty"`
	Formats     []Format `json:"formats,omitempty"`
	UploadDate  string   `json:"upload_date,omitempty"`
}

// Format represents a video format option
type Format struct {
	FormatID   string `json:"format_id"`
	URL        string `json:"url"`
	Extension  string `json:"ext"`
	Quality    string `json:"quality"`
	Resolution string `json:"resolution,omitempty"`
	Filesize   int64  `json:"filesize,omitempty"`
	Bitrate    int    `json:"bitrate,omitempty"`
	Codec      string `json:"codec,omitempty"`
}

// StreamRequest represents a streaming request
type StreamRequest struct {
	Platform string `json:"platform" binding:"required"`
	VideoID  string `json:"video_id" binding:"required"`
	Quality  string `json:"quality"`
	Format   string `json:"format"`
}

// StreamResponse represents a streaming response
type StreamResponse struct {
	Success   bool      `json:"success"`
	StreamURL string    `json:"stream_url,omitempty"`
	VideoInfo VideoInfo `json:"video_info,omitempty"`
	CachedAt  time.Time `json:"cached_at,omitempty"`
	ExpiresAt time.Time `json:"expires_at,omitempty"`
}

// PlaylistInfo represents playlist metadata
type PlaylistInfo struct {
	ID          string          `json:"id"`
	Title       string          `json:"title"`
	Description string          `json:"description,omitempty"`
	Uploader    string          `json:"uploader,omitempty"`
	WebpageURL  string          `json:"webpage_url,omitempty"`
	EntryCount  int             `json:"entry_count"`
	Platform    string          `json:"platform"`
	Entries     []PlaylistEntry `json:"entries"`
}

// PlaylistEntry represents a video entry inside a playlist
type PlaylistEntry struct {
	ID         string `json:"id"`
	Title      string `json:"title"`
	Duration   int    `json:"duration,omitempty"`
	Uploader   string `json:"uploader,omitempty"`
	WebpageURL string `json:"webpage_url,omitempty"`
}

// HealthResponse represents system health status
type HealthResponse struct {
	Status    string            `json:"status"`
	Timestamp time.Time         `json:"timestamp"`
	Version   string            `json:"version"`
	Services  map[string]string `json:"services"`
	Uptime    string            `json:"uptime"`
	Memory    MemoryStats       `json:"memory"`
}

// MemoryStats represents memory usage statistics
type MemoryStats struct {
	Alloc      uint64 `json:"alloc_mb"`
	TotalAlloc uint64 `json:"total_alloc_mb"`
	Sys        uint64 `json:"sys_mb"`
	NumGC      uint32 `json:"num_gc"`
}

// AuthStatus represents authentication status
type AuthStatus struct {
	Platform      string    `json:"platform"`
	Authenticated bool      `json:"authenticated"`
	Username      string    `json:"username,omitempty"`
	ExpiresAt     time.Time `json:"expires_at,omitempty"`
	CookiesValid  bool      `json:"cookies_valid"`
}

// BatchRequest represents a batch video processing request
type BatchRequest struct {
	Videos        []VideoRequest `json:"videos" binding:"required"`
	Parallel      bool           `json:"parallel"`
	MaxConcurrent int            `json:"max_concurrent"`
}

// VideoRequest represents a single video request
type VideoRequest struct {
	URL       string `json:"url" binding:"required"`
	Quality   string `json:"quality"`
	Format    string `json:"format"`
	AudioOnly bool   `json:"audio_only"`
}

// BatchResponse represents a batch processing response
type BatchResponse struct {
	Success   bool          `json:"success"`
	Total     int           `json:"total"`
	Completed int           `json:"completed"`
	Failed    int           `json:"failed"`
	Results   []VideoResult `json:"results"`
	Duration  float64       `json:"duration_seconds"`
}

// VideoResult represents the result of processing a single video
type VideoResult struct {
	URL       string    `json:"url"`
	Success   bool      `json:"success"`
	VideoInfo VideoInfo `json:"video_info,omitempty"`
	Error     string    `json:"error,omitempty"`
}

// ErrorResponse represents an API error response
type ErrorResponse struct {
	Success   bool      `json:"success"`
	Error     string    `json:"error"`
	Detail    string    `json:"detail,omitempty"`
	Code      string    `json:"code"`
	Timestamp time.Time `json:"timestamp"`
}

// SuccessResponse represents a successful API response
type SuccessResponse struct {
	Success   bool        `json:"success"`
	Message   string      `json:"message"`
	Data      interface{} `json:"data,omitempty"`
	Timestamp time.Time   `json:"timestamp"`
}

// StreamMetrics represents streaming performance metrics
type StreamMetrics struct {
	TotalRequests    int64   `json:"total_requests"`
	CacheHits        int64   `json:"cache_hits"`
	CacheMisses      int64   `json:"cache_misses"`
	CacheHitRate     float64 `json:"cache_hit_rate"`
	AverageLatencyMs float64 `json:"average_latency_ms"`
	TotalBytesServed int64   `json:"total_bytes_served"`
	ActiveStreams    int     `json:"active_streams"`
}
