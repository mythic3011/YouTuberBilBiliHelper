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

// Version represents the application version, set via ldflags during build or defaults to "dev".
var Version = "dev"

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
// @BasePath

// @schemes http https

func main() {
	// Load configuration
	cfg := config.Load()

	// Setup logger
	logger := setupLogger(cfg)
	logger.Info("Starting Go Video Streaming API...")

	// Validate security configuration
	if err := cfg.Security.Validate(); err != nil {
		logger.WithError(err).Fatal("Security configuration validation failed")
	}
	logger.Info("Security configuration validated")

	// Initialize services
	redisService := services.NewRedisService(cfg, logger)
	videoService := services.NewVideoService(redisService, cfg, logger)
	streamingService := services.NewStreamingService(videoService, redisService, cfg, logger)
	systemService := services.NewSystemService(redisService, cfg, logger)

	// Initialize security components
	securityComponents, err := initSecurityComponents(cfg, logger)
	if err != nil {
		logger.WithError(err).Fatal("Failed to initialize security components")
	}
	logger.Info("Security components initialized")

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
	handler := api.NewHandler(videoService, streamingService, systemService, logger, cfg)

	// Setup routes with security middleware
	if securityComponents != nil {
		api.SetupRoutesWithSecurity(router, handler, logger, securityComponents)
		logger.Info("Routes configured with security middleware")
	} else {
		api.SetupRoutes(router, handler, logger)
		logger.Info("Routes configured without security middleware")
	}

	// Start server
	addr := fmt.Sprintf(":%s", cfg.Port)
	logger.WithField("port", cfg.Port).Info("Server starting")

	// Graceful shutdown
	srv := setupServer(addr, router)

	// Start server in goroutine
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
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

	// Close audit logger if initialized
	if securityComponents != nil && securityComponents.AuditLogger != nil {
		if fileLogger, ok := securityComponents.AuditLogger.(*services.FileAuditLogger); ok {
			if err := fileLogger.Close(); err != nil {
				logger.WithError(err).Error("Failed to close audit logger")
			}
		}
	}

	// Close Redis connection
	if err := redisService.Close(); err != nil {
		logger.WithError(err).Error("Failed to close Redis connection")
	}

	logger.Info("Server stopped")
}

// initSecurityComponents initializes all security-related components
func initSecurityComponents(cfg *config.Config, logger *logrus.Logger) (*api.SecurityComponents, error) {
	securityCfg := &cfg.Security

	// Initialize audit logger
	var auditLogger services.AuditLogger
	if securityCfg.EnableAuditLog {
		var err error
		auditLogger, err = services.NewFileAuditLogger(securityCfg.AuditLogPath, logger, true)
		if err != nil {
			return nil, fmt.Errorf("failed to initialize audit logger: %w", err)
		}
		logger.WithField("path", securityCfg.AuditLogPath).Info("Audit logger initialized")
	}

	// Initialize IP access controller
	var ipController *api.CIDRAccessController
	if securityCfg.EnableIPControl {
		var err error
		ipController, err = api.NewCIDRAccessController(securityCfg.IPAllowlist, securityCfg.IPBlocklist, true)
		if err != nil {
			return nil, fmt.Errorf("failed to initialize IP access controller: %w", err)
		}
		logger.WithFields(logrus.Fields{
			"allowlist_count": len(securityCfg.IPAllowlist),
			"blocklist_count": len(securityCfg.IPBlocklist),
		}).Info("IP access controller initialized")
	}

	// Initialize secure error handler
	secureErrorHandler := api.NewSecureErrorHandler(logger, securityCfg.ExposeDetailedErrors)

	return &api.SecurityComponents{
		Config:             securityCfg,
		AuditLogger:        auditLogger,
		IPAccessController: ipController,
		SecureErrorHandler: secureErrorHandler,
	}, nil
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
