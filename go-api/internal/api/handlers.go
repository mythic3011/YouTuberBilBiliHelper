package api

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	"video-streaming-api/internal/models"
	"video-streaming-api/internal/services"
)

// Handler holds all HTTP handlers
type Handler struct {
	video     *services.VideoService
	streaming *services.StreamingService
	system    *services.SystemService
	logger    *logrus.Logger
}

// NewHandler creates a new handler
func NewHandler(
	video *services.VideoService,
	streaming *services.StreamingService,
	system *services.SystemService,
	logger *logrus.Logger,
) *Handler {
	return &Handler{
		video:     video,
		streaming: streaming,
		system:    system,
		logger:    logger,
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

// StreamVideoProxy handles video streaming through proxy
func (h *Handler) StreamVideoProxy(c *gin.Context) {
	platform := c.Param("platform")
	videoID := c.Param("video_id")
	quality := c.DefaultQuery("quality", "best")

	if !h.video.ValidatePlatform(platform) {
		h.errorResponse(c, http.StatusBadRequest, "Unsupported platform", platform)
		return
	}

	h.logger.WithFields(logrus.Fields{
		"platform": platform,
		"video_id": videoID,
		"quality":  quality,
	}).Info("Streaming video request")

	if err := h.streaming.StreamVideo(c, platform, videoID, quality); err != nil {
		h.logger.WithError(err).Error("Failed to stream video")
		if !c.Writer.Written() {
			h.errorResponse(c, http.StatusInternalServerError, "Failed to stream video", err.Error())
		}
	}
}

// GetDirectStreamURL handles direct stream URL requests
func (h *Handler) GetDirectStreamURL(c *gin.Context) {
	platform := c.Param("platform")
	videoID := c.Param("video_id")
	quality := c.DefaultQuery("quality", "best")

	if !h.video.ValidatePlatform(platform) {
		h.errorResponse(c, http.StatusBadRequest, "Unsupported platform", platform)
		return
	}

	streamURL, err := h.streaming.GetDirectStreamURL(c.Request.Context(), platform, videoID, quality)
	if err != nil {
		h.logger.WithError(err).WithFields(logrus.Fields{
			"platform": platform,
			"video_id": videoID,
		}).Error("Failed to get stream URL")
		h.errorResponse(c, http.StatusBadRequest, "Failed to get stream URL", err.Error())
		return
	}

	// Redirect to stream URL
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

