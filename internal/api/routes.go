package api

import (
	"video-streaming-api/internal/config"
	"video-streaming-api/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

// SecurityComponents holds all security-related components for middleware
type SecurityComponents struct {
	Config             *config.SecurityConfig
	AuditLogger        services.AuditLogger
	IPAccessController *CIDRAccessController
	SecureErrorHandler *SecureErrorHandler
}

// SetupRoutes configures all API routes
func SetupRoutes(router *gin.Engine, handler *Handler, logger *logrus.Logger) {
	// Apply global middleware (basic setup without security components)
	router.Use(LoggerMiddleware(logger))
	router.Use(CORSMiddleware())
	router.Use(SecurityHeadersMiddleware())
	router.Use(RecoveryMiddleware(logger))

	setupCommonRoutes(router, handler)
}

// SetupRoutesWithSecurity configures all API routes with full security middleware stack
// Middleware order: IP Access → Size Limits → Validation → Sanitization → Security Headers
func SetupRoutesWithSecurity(router *gin.Engine, handler *Handler, logger *logrus.Logger, security *SecurityComponents) {
	// 1. IP Access Control Middleware (earliest - blocks before processing)
	if security.IPAccessController != nil && security.Config.EnableIPControl {
		router.Use(IPAccessControlMiddleware(security.IPAccessController, logger))
	}

	// 2. Request Size Limit Middleware
	router.Use(RequestSizeLimitMiddleware(security.Config, logger))

	// 3. Input Validation Middleware
	validator := NewDefaultInputValidator(security.Config)
	router.Use(ValidationMiddleware(validator, logger))

	// 4. Input Sanitization Middleware
	sanitizer := NewDefaultInputSanitizer()
	router.Use(SanitizationMiddleware(sanitizer, logger))

	// 5. Enhanced Security Headers Middleware
	router.Use(EnhancedSecurityHeadersMiddleware(security.Config))

	// 6. Logging Middleware
	router.Use(LoggerMiddleware(logger))

	// 7. CORS Middleware
	router.Use(CORSMiddleware())

	// 8. Recovery Middleware with audit logging
	if security.SecureErrorHandler != nil {
		router.Use(SecureRecoveryMiddleware(security.SecureErrorHandler))
	} else if security.AuditLogger != nil {
		router.Use(AuditRecoveryMiddleware(logger, security.AuditLogger))
	} else {
		router.Use(RecoveryMiddleware(logger))
	}

	setupCommonRoutes(router, handler)
}

// setupCommonRoutes sets up the common route handlers
func setupCommonRoutes(router *gin.Engine, handler *Handler) {
	// Root endpoint
	router.GET("/", handler.Root)
	router.GET("/health", handler.GetHealth)

	// Swagger documentation
	router.GET("/docs/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	// API v2 routes (matching Python API)
	v2 := router.Group("/api/v2")
	{
		// System routes
		system := v2.Group("/system")
		{
			system.GET("/health", handler.GetHealth)
		}

		// Streaming routes
		stream := v2.Group("/stream")
		{
			stream.GET("/:platform/*video_id", handler.StreamVideo)
			stream.GET("/metrics", handler.GetStreamMetrics)
		}

		// Video routes
		videos := v2.Group("/videos")
		{
			videos.GET("/:platform/:video_id", handler.GetVideoInfo)
		}

		// Playlist routes
		playlists := v2.Group("/playlists")
		{
			playlists.GET("/:platform/:playlist_id", handler.GetPlaylistInfo)
		}
	}
}
