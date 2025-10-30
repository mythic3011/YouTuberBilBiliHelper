package api

import (
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

// SetupRoutes configures all API routes
func SetupRoutes(router *gin.Engine, handler *Handler, logger *logrus.Logger) {
	// Apply global middleware
	router.Use(LoggerMiddleware(logger))
	router.Use(CORSMiddleware())
	router.Use(SecurityHeadersMiddleware())
	router.Use(RecoveryMiddleware(logger))

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
			stream.GET("/proxy/:platform/:video_id", handler.StreamVideoProxy)
			stream.GET("/direct/:platform/:video_id", handler.GetDirectStreamURL)
			stream.GET("/metrics", handler.GetStreamMetrics)
		}

		// Video routes
		videos := v2.Group("/videos")
		{
			videos.GET("/:platform/:video_id", handler.GetVideoInfo)
		}
	}
}

