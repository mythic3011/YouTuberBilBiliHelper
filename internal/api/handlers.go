package api

import (
	"net/http"
	"strings"
	"time"

	"video-streaming-api/internal/config"
	"video-streaming-api/internal/models"
	"video-streaming-api/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// Handler holds all HTTP handlers
type Handler struct {
	video     *services.VideoService
	streaming *services.StreamingService
	system    *services.SystemService
	logger    *logrus.Logger
	cfg       *config.Config
}

// NewHandler creates a new handler
func NewHandler(
	video *services.VideoService,
	streaming *services.StreamingService,
	system *services.SystemService,
	logger *logrus.Logger,
	cfg *config.Config,
) *Handler {
	return &Handler{
		video:     video,
		streaming: streaming,
		system:    system,
		logger:    logger,
		cfg:       cfg,
	}
}

// Root godoc
// @Summary      Root endpoint
// @Description  Get API information and available endpoints
// @Tags         root
// @Produce      json
// @Success      200  {object}  map[string]interface{}
// @Router       / [get]
func (h *Handler) Root(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"name":        "Go Video Streaming API",
		"version":     "2.0.0",
		"description": "High-performance video streaming API built with Go",
		"docs_url":    "/docs",
		"health_url":  "/api/v2/system/health",
		"endpoints": gin.H{
			"health":    "/api/v2/system/health",
			"streaming": "/api/v2/stream/proxy/:platform/:video_id",
			"direct":    "/api/v2/stream/direct/:platform/:video_id",
			"smart":     "/api/v2/stream/smart/:platform/:video_id",
			"info":      "/api/v2/videos/:platform/:video_id",
		},
		"supported_platforms": []string{"youtube", "bilibili", "twitter", "instagram", "twitch"},
		"timestamp":           time.Now(),
	})
}

// GetHealth godoc
// @Summary      Health check
// @Description  Check API and service health status
// @Tags         system
// @Produce      json
// @Success      200  {object}  models.HealthResponse
// @Failure      503  {object}  models.HealthResponse
// @Router       /health [get]
// @Router       /api/v2/system/health [get]
func (h *Handler) GetHealth(c *gin.Context) {
	health, err := h.system.GetHealth(c.Request.Context())
	if err != nil {
		h.errorResponse(c, http.StatusInternalServerError, "Health check failed", err.Error())
		return
	}

	statusCode := http.StatusOK
	if health.Status != "healthy" {
		statusCode = http.StatusServiceUnavailable
	}

	c.JSON(statusCode, health)
}

// GetVideoInfo godoc
// @Summary      Get video information
// @Description  Retrieve video metadata from various platforms
// @Tags         videos
// @Produce      json
// @Param        platform  path      string  true  "Platform (youtube, bilibili, twitter, instagram, twitch)"
// @Param        video_id  path      string  true  "Video ID"
// @Success      200       {object}  models.VideoInfo
// @Failure      400       {object}  models.ErrorResponse
// @Failure      404       {object}  models.ErrorResponse
// @Router       /api/v2/videos/{platform}/{video_id} [get]
func (h *Handler) GetVideoInfo(c *gin.Context) {
	platform := c.Param("platform")
	videoID := c.Param("video_id")

	if !h.video.ValidatePlatform(platform) {
		h.errorResponse(c, http.StatusBadRequest, "Unsupported platform", platform)
		return
	}

	info, err := h.video.GetVideoInfo(c.Request.Context(), platform, videoID)
	if err != nil {
		h.logger.WithError(err).WithFields(logrus.Fields{
			"platform": platform,
			"video_id": videoID,
		}).Error("Failed to get video info")
		h.errorResponse(c, http.StatusBadRequest, "Failed to get video info", err.Error())
		return
	}

	c.JSON(http.StatusOK, models.SuccessResponse{
		Success:   true,
		Message:   "Video information retrieved successfully",
		Data:      info,
		Timestamp: time.Now(),
	})
}

// GetPlaylistInfo godoc
// @Summary      Get playlist information
// @Description  Retrieve playlist metadata and entries
// @Tags         playlists
// @Produce      json
// @Param        platform    path      string  true  "Platform (youtube, bilibili, etc.)"
// @Param        playlist_id path      string  true  "Playlist ID or URL"
// @Success      200         {object}  models.PlaylistInfo
// @Failure      400         {object}  models.ErrorResponse
// @Router       /api/v2/playlists/{platform}/{playlist_id} [get]
func (h *Handler) GetPlaylistInfo(c *gin.Context) {
	platform := c.Param("platform")
	playlistID := c.Param("playlist_id")

	if !h.video.ValidatePlatform(platform) {
		h.errorResponse(c, http.StatusBadRequest, "Unsupported platform", platform)
		return
	}

	info, err := h.video.GetPlaylistInfo(c.Request.Context(), platform, playlistID)
	if err != nil {
		h.logger.WithError(err).WithFields(logrus.Fields{
			"platform":    platform,
			"playlist_id": playlistID,
		}).Error("Failed to get playlist info")
		h.errorResponse(c, http.StatusBadRequest, "Failed to get playlist info", err.Error())
		return
	}

	c.JSON(http.StatusOK, models.SuccessResponse{
		Success:   true,
		Message:   "Playlist information retrieved successfully",
		Data:      info,
		Timestamp: time.Now(),
	})
}

// StreamVideo handles smart streaming decisions.
// @Summary      Stream video (smart proxy/direct)
// @Description  Automatically proxies traffic for configured countries (defaults to CN) while serving others via direct redirect; can be overridden via query parameters.
// @Tags         stream
// @Produce      json
// @Param        platform  path      string  true  "Platform (youtube, bilibili, etc.)"
// @Param        video_id  path      string  true  "Video ID or URL"
// @Param        quality   query     string  false "Preferred quality"
// @Param        mode      query     string  false "Force 'proxy' or 'direct'"
// @Success      302       {string}  string  "Redirect or proxied stream"
// @Failure      400       {object}  models.ErrorResponse
// @Router       /api/v2/stream/{platform}/{video_id} [get]
func (h *Handler) StreamVideo(c *gin.Context) {
	platform := c.Param("platform")
	videoID := strings.TrimPrefix(c.Param("video_id"), "/")
	
	// Handle URL passed in path (e.g., /api/v2/stream/https:/www.youtube.com/watch?v=...)
	// Reconstruct full URL if platform looks like a URL scheme
	if platform == "http:" || platform == "https:" {
		// Reconstruct the full URL from the request
		fullURL := platform + videoID
		// If query parameters exist, append them
		if rawQuery := c.Request.URL.RawQuery; rawQuery != "" {
			fullURL += "?" + rawQuery
		}
		
		// Detect platform from URL
		detectedPlatform := h.video.DetectPlatform(fullURL)
		if detectedPlatform == "unknown" {
			h.errorResponse(c, http.StatusBadRequest, "Cannot detect platform from URL", fullURL)
			return
		}
		platform = detectedPlatform
		videoID = fullURL
	}
	
	quality := c.DefaultQuery("quality", "best")
	mode := strings.ToLower(c.DefaultQuery("mode", ""))

	if !h.video.ValidatePlatform(platform) {
		h.errorResponse(c, http.StatusBadRequest, "Unsupported platform", platform)
		return
	}

	useProxy := h.cfg != nil && strings.EqualFold(h.cfg.DefaultStreamMode, "proxy")
	if mode == "proxy" {
		useProxy = true
	} else if mode == "direct" {
		useProxy = false
	} else if h.cfg == nil || h.cfg.SmartProxyEnabled {
		useProxy = h.shouldProxyRequest(c)
	}

	modeLabel := "direct"
	if useProxy {
		modeLabel = "proxy"
	}
	reqFields := logrus.Fields{
		"platform": platform,
		"video_id": videoID,
		"quality":  quality,
		"mode":     modeLabel,
		"country":  strings.ToUpper(h.detectCountry(c)),
	}

	if useProxy {
		h.logger.WithFields(reqFields).Info("Smart streaming via proxy")
		if err := h.streaming.StreamVideo(c, platform, videoID, quality); err != nil {
			h.logger.WithError(err).Error("Failed to stream video")
			if !c.Writer.Written() {
				h.errorResponse(c, http.StatusInternalServerError, "Failed to stream video", err.Error())
			}
		}
		return
	}

	streamURL, err := h.streaming.GetDirectStreamURL(c.Request.Context(), platform, videoID, quality)
	if err != nil {
		h.logger.WithError(err).WithFields(reqFields).Error("Failed to get stream URL")
		h.errorResponse(c, http.StatusBadRequest, "Failed to get stream URL", err.Error())
		return
	}

	h.logger.WithFields(reqFields).Info("Smart streaming via direct redirect")
	c.Redirect(http.StatusFound, streamURL)
}

// GetStreamMetrics handles streaming metrics requests
func (h *Handler) GetStreamMetrics(c *gin.Context) {
	metrics := h.streaming.GetMetrics()
	c.JSON(http.StatusOK, models.SuccessResponse{
		Success:   true,
		Message:   "Streaming metrics retrieved successfully",
		Data:      metrics,
		Timestamp: time.Now(),
	})
}

// errorResponse sends a standardized error response
func (h *Handler) errorResponse(c *gin.Context, statusCode int, message, detail string) {
	c.JSON(statusCode, models.ErrorResponse{
		Success:   false,
		Error:     message,
		Detail:    detail,
		Code:      http.StatusText(statusCode),
		Timestamp: time.Now(),
	})
}

func (h *Handler) shouldProxyRequest(c *gin.Context) bool {
	if h.cfg == nil {
		return false
	}
	country := strings.ToUpper(h.detectCountry(c))
	if country == "" {
		return strings.EqualFold(h.cfg.DefaultStreamMode, "proxy")
	}
	for _, code := range h.cfg.ProxyCountries {
		if strings.EqualFold(code, country) {
			return true
		}
	}
	return false
}

func (h *Handler) detectCountry(c *gin.Context) string {
	if override := strings.TrimSpace(c.DefaultQuery("country", "")); override != "" {
		return strings.ToUpper(override)
	}
	headers := []string{"CF-IPCountry", "X-Country-Code", "X-Appengine-Country", "X-Geo-Country"}
	for _, header := range headers {
		if val := strings.TrimSpace(c.GetHeader(header)); val != "" && val != "ZZ" && val != "XX" {
			return strings.ToUpper(val)
		}
	}
	return ""
}
