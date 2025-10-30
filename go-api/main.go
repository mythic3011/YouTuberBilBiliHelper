package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"

	_ "video-streaming-api/docs" // Swagger docs
	"video-streaming-api/internal/api"
	"video-streaming-api/internal/config"
	"video-streaming-api/internal/services"
)

// @title           Video Streaming API
// @version         1.0
// @description     High-performance video streaming and processing API built with Go
// @termsOfService  http://swagger.io/terms/

// @contact.name   API Support
// @contact.url    http://www.swagger.io/support
// @contact.email  support@swagger.io

// @license.name  MIT
// @license.url   https://opensource.org/licenses/MIT

// @host      localhost:8001
// @BasePath  /

// @schemes http https

func main() {
	// Load configuration
	cfg := config.Load()

	// Setup logger
	logger := setupLogger(cfg)
	logger.Info("Starting Go Video Streaming API...")

	// Initialize services
	redisService := services.NewRedisService(cfg, logger)
	videoService := services.NewVideoService(redisService, cfg, logger)
	streamingService := services.NewStreamingService(videoService, redisService, cfg, logger)
	systemService := services.NewSystemService(redisService, cfg, logger)

	// Test Redis connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := redisService.Ping(ctx); err != nil {
		logger.WithError(err).Warn("Failed to connect to Redis - caching disabled")
	} else {
		logger.Info("Redis connection established")
	}

	// Setup Gin
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Create handler
	handler := api.NewHandler(videoService, streamingService, systemService, logger)

	// Setup routes
	api.SetupRoutes(router, handler, logger)

	// Start server
	addr := fmt.Sprintf(":%s", cfg.Port)
	logger.WithField("port", cfg.Port).Info("Server starting")

	// Graceful shutdown
	srv := setupServer(addr, router)
	
	// Start server in goroutine
	go func() {
		if err := srv.ListenAndServe(); err != nil {
			logger.WithError(err).Fatal("Server failed to start")
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.WithError(err).Error("Server forced to shutdown")
	}

	// Close Redis connection
	if err := redisService.Close(); err != nil {
		logger.WithError(err).Error("Failed to close Redis connection")
	}

	logger.Info("Server stopped")
}

func setupLogger(cfg *config.Config) *logrus.Logger {
	logger := logrus.New()

	// Set log level
	level, err := logrus.ParseLevel(cfg.LogLevel)
	if err != nil {
		level = logrus.InfoLevel
	}
	logger.SetLevel(level)

	// Set formatter
	if cfg.Environment == "production" {
		logger.SetFormatter(&logrus.JSONFormatter{
			TimestampFormat: time.RFC3339,
		})
	} else {
		logger.SetFormatter(&logrus.TextFormatter{
			FullTimestamp:   true,
			TimestampFormat: "2006-01-02 15:04:05",
		})
	}

	return logger
}

func setupServer(addr string, handler *gin.Engine) *http.Server {
	return &http.Server{
		Addr:           addr,
		Handler:        handler,
		ReadTimeout:    30 * time.Second,
		WriteTimeout:   30 * time.Second,
		MaxHeaderBytes: 1 << 20, // 1 MB
	}
}

