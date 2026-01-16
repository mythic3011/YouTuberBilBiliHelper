package api

import (
	"fmt"
	"net/http"
	"runtime/debug"
	"time"

	"video-streaming-api/internal/config"
	"video-streaming-api/internal/models"
	"video-streaming-api/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// Context keys for validated parameters
const (
	ValidatedPlatformKey   = "validated_platform"
	ValidatedVideoIDKey    = "validated_video_id"
	ValidatedPlaylistIDKey = "validated_playlist_id"
	ValidatedQualityKey    = "validated_quality"
	ValidatedCountryKey    = "validated_country"
	ValidatedModeKey       = "validated_mode"
)

// LoggerMiddleware logs HTTP requests
func LoggerMiddleware(logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		// Process request
		c.Next()

		// Log after processing
		latency := time.Since(start)
		statusCode := c.Writer.Status()
		clientIP := c.ClientIP()
		method := c.Request.Method
		userAgent := c.Request.UserAgent()
		referer := c.Request.Referer()

		logger.WithFields(logrus.Fields{
			"status_code": statusCode,
			"latency_ms":  latency.Milliseconds(),
			"client_ip":   clientIP,
			"method":      method,
			"path":        path,
			"query":       query,
			"user_agent":  userAgent,
			"referer":     referer,
		}).Info("HTTP request")
	}
}

// CORSMiddleware handles CORS
func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

// SecurityHeadersMiddleware adds security headers (legacy version without config)
func SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("X-Content-Type-Options", "nosniff")
		c.Writer.Header().Set("X-Frame-Options", "DENY")
		c.Writer.Header().Set("X-XSS-Protection", "1; mode=block")
		c.Next()
	}
}

// EnhancedSecurityHeadersMiddleware adds comprehensive security headers with configuration.
// Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
func EnhancedSecurityHeadersMiddleware(cfg *config.SecurityConfig) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Content-Security-Policy (Requirement 3.1)
		if cfg.CSPDirectives != "" {
			c.Writer.Header().Set("Content-Security-Policy", cfg.CSPDirectives)
		}

		// Strict-Transport-Security (Requirement 3.2, 3.8)
		if cfg.EnableHSTS {
			hstsValue := fmt.Sprintf("max-age=%d; includeSubDomains; preload", cfg.HSTSMaxAge)
			c.Writer.Header().Set("Strict-Transport-Security", hstsValue)
		}

		// Referrer-Policy (Requirement 3.3)
		if cfg.ReferrerPolicy != "" {
			c.Writer.Header().Set("Referrer-Policy", cfg.ReferrerPolicy)
		}

		// Permissions-Policy (Requirement 3.4)
		if cfg.PermissionsPolicy != "" {
			c.Writer.Header().Set("Permissions-Policy", cfg.PermissionsPolicy)
		}

		// X-Content-Type-Options (Requirement 3.5)
		c.Writer.Header().Set("X-Content-Type-Options", "nosniff")

		// X-Frame-Options (Requirement 3.6)
		c.Writer.Header().Set("X-Frame-Options", "DENY")

		// X-XSS-Protection (Requirement 3.7)
		c.Writer.Header().Set("X-XSS-Protection", "1; mode=block")

		c.Next()
	}
}

// RecoveryMiddleware recovers from panics
func RecoveryMiddleware(logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				logger.WithFields(logrus.Fields{
					"error": err,
					"path":  c.Request.URL.Path,
				}).Error("Panic recovered")

				c.JSON(500, gin.H{
					"success":   false,
					"error":     "Internal Server Error",
					"detail":    "An unexpected error occurred",
					"code":      "INTERNAL_ERROR",
					"timestamp": time.Now(),
				})
				c.Abort()
			}
		}()
		c.Next()
	}
}

// AuditRecoveryMiddleware recovers from panics with audit logging.
// Requirements: 6.4
func AuditRecoveryMiddleware(logger *logrus.Logger, auditLogger services.AuditLogger) gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := ""
		if auditLogger != nil {
			requestID = auditLogger.GenerateRequestID()
			c.Set("request_id", requestID)
		}

		defer func() {
			if err := recover(); err != nil {
				stack := string(debug.Stack())

				logger.WithFields(logrus.Fields{
					"error":      err,
					"path":       c.Request.URL.Path,
					"request_id": requestID,
				}).Error("Panic recovered")

				// Log to audit log
				if auditLogger != nil {
					auditLogger.LogPanicRecovered(
						requestID,
						c.ClientIP(),
						c.Request.Method,
						c.Request.URL.Path,
						c.Request.UserAgent(),
						err,
						stack,
					)
				}

				c.JSON(500, gin.H{
					"success":    false,
					"error":      "Internal Server Error",
					"detail":     "An unexpected error occurred",
					"code":       "INTERNAL_ERROR",
					"request_id": requestID,
					"timestamp":  time.Now(),
				})
				c.Abort()
			}
		}()
		c.Next()
	}
}


// ValidationErrorResponse represents a structured validation error response.
type ValidationErrorResponse struct {
	Success    bool              `json:"success"`
	Error      string            `json:"error"`
	Validation []ValidationError `json:"validation"`
	Timestamp  time.Time         `json:"timestamp"`
}

// ValidationMiddleware validates request parameters and returns 400 on failure.
// Requirements: 1.7
func ValidationMiddleware(validator InputValidator, logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		var validationErrors []ValidationError

		// Extract and validate platform parameter (path param)
		platform := c.Param("platform")
		if platform != "" {
			if err := validator.ValidatePlatform(platform); err != nil {
				if ve, ok := err.(*ValidationError); ok {
					validationErrors = append(validationErrors, *ve)
				}
			} else {
				c.Set(ValidatedPlatformKey, platform)
			}
		}

		// Extract and validate video_id parameter (path param)
		videoID := c.Param("video_id")
		if videoID != "" {
			if err := validator.ValidateVideoID(videoID); err != nil {
				if ve, ok := err.(*ValidationError); ok {
					validationErrors = append(validationErrors, *ve)
				}
			} else {
				c.Set(ValidatedVideoIDKey, videoID)
			}
		}

		// Extract and validate playlist_id parameter (path param)
		playlistID := c.Param("playlist_id")
		if playlistID != "" {
			if err := validator.ValidatePlaylistID(playlistID); err != nil {
				if ve, ok := err.(*ValidationError); ok {
					validationErrors = append(validationErrors, *ve)
				}
			} else {
				c.Set(ValidatedPlaylistIDKey, playlistID)
			}
		}

		// Extract and validate quality parameter (query param)
		quality := c.Query("quality")
		if err := validator.ValidateQuality(quality); err != nil {
			if ve, ok := err.(*ValidationError); ok {
				validationErrors = append(validationErrors, *ve)
			}
		} else {
			c.Set(ValidatedQualityKey, quality)
		}

		// Extract and validate country parameter (query param)
		country := c.Query("country")
		if err := validator.ValidateCountryCode(country); err != nil {
			if ve, ok := err.(*ValidationError); ok {
				validationErrors = append(validationErrors, *ve)
			}
		} else {
			c.Set(ValidatedCountryKey, country)
		}

		// Extract and validate mode parameter (query param)
		mode := c.Query("mode")
		if err := validator.ValidateMode(mode); err != nil {
			if ve, ok := err.(*ValidationError); ok {
				validationErrors = append(validationErrors, *ve)
			}
		} else {
			c.Set(ValidatedModeKey, mode)
		}

		// If there are validation errors, return 400 Bad Request
		if len(validationErrors) > 0 {
			// Log validation failures
			for _, ve := range validationErrors {
				logger.WithFields(logrus.Fields{
					"client_ip": c.ClientIP(),
					"path":      c.Request.URL.Path,
					"field":     ve.Field,
					"value":     ve.Value,
					"message":   ve.Message,
					"code":      ve.Code,
				}).Warn("Validation failure")
			}

			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Success:   false,
				Error:     "Validation failed",
				Detail:    validationErrors[0].Message,
				Code:      "VALIDATION_ERROR",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}


// SanitizationMiddleware sanitizes request parameters and rejects malicious inputs.
// Requirements: 2.4, 2.5
func SanitizationMiddleware(sanitizer InputSanitizer, logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		clientIP := c.ClientIP()
		path := c.Request.URL.Path

		// Check path parameters for null bytes and control characters
		for _, param := range c.Params {
			if sanitizer.ContainsNullOrControlChars(param.Value) {
				logger.WithFields(logrus.Fields{
					"client_ip": clientIP,
					"path":      path,
					"param":     param.Key,
					"reason":    "null_or_control_chars",
				}).Warn("Sanitization rejected request: null bytes or control characters")

				c.JSON(http.StatusBadRequest, models.ErrorResponse{
					Success:   false,
					Error:     "Invalid request",
					Detail:    "Request contains invalid characters",
					Code:      "INVALID_CHARACTERS",
					Timestamp: time.Now(),
				})
				c.Abort()
				return
			}

			// Check for malicious patterns
			if detected, patternType := sanitizer.DetectMaliciousPatterns(param.Value); detected {
				logger.WithFields(logrus.Fields{
					"client_ip":    clientIP,
					"path":         path,
					"param":        param.Key,
					"pattern_type": patternType,
				}).Warn("Sanitization detected malicious pattern")

				c.JSON(http.StatusBadRequest, models.ErrorResponse{
					Success:   false,
					Error:     "Invalid request",
					Detail:    "Request contains potentially malicious content",
					Code:      "MALICIOUS_CONTENT",
					Timestamp: time.Now(),
				})
				c.Abort()
				return
			}
		}

		// Check query parameters
		for key, values := range c.Request.URL.Query() {
			for _, value := range values {
				if sanitizer.ContainsNullOrControlChars(value) {
					logger.WithFields(logrus.Fields{
						"client_ip": clientIP,
						"path":      path,
						"param":     key,
						"reason":    "null_or_control_chars",
					}).Warn("Sanitization rejected request: null bytes or control characters in query")

					c.JSON(http.StatusBadRequest, models.ErrorResponse{
						Success:   false,
						Error:     "Invalid request",
						Detail:    "Query parameter contains invalid characters",
						Code:      "INVALID_CHARACTERS",
						Timestamp: time.Now(),
					})
					c.Abort()
					return
				}

				// Check for malicious patterns in query params
				if detected, patternType := sanitizer.DetectMaliciousPatterns(value); detected {
					logger.WithFields(logrus.Fields{
						"client_ip":    clientIP,
						"path":         path,
						"param":        key,
						"pattern_type": patternType,
					}).Warn("Sanitization detected malicious pattern in query")

					c.JSON(http.StatusBadRequest, models.ErrorResponse{
						Success:   false,
						Error:     "Invalid request",
						Detail:    "Query parameter contains potentially malicious content",
						Code:      "MALICIOUS_CONTENT",
						Timestamp: time.Now(),
					})
					c.Abort()
					return
				}
			}
		}

		// Check the URL path itself
		if sanitizer.ContainsNullOrControlChars(path) {
			logger.WithFields(logrus.Fields{
				"client_ip": clientIP,
				"path":      path,
				"reason":    "null_or_control_chars_in_path",
			}).Warn("Sanitization rejected request: null bytes or control characters in path")

			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Success:   false,
				Error:     "Invalid request",
				Detail:    "URL path contains invalid characters",
				Code:      "INVALID_CHARACTERS",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}


// RequestSizeLimitMiddleware enforces size limits on incoming requests.
// Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
func RequestSizeLimitMiddleware(cfg *config.SecurityConfig, logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		clientIP := c.ClientIP()

		// Check URL length (Requirement 4.2)
		urlLength := len(c.Request.URL.String())
		if urlLength > cfg.MaxURLLength {
			logger.WithFields(logrus.Fields{
				"client_ip":  clientIP,
				"url_length": urlLength,
				"max_length": cfg.MaxURLLength,
				"path":       c.Request.URL.Path,
			}).Warn("Request URL exceeds size limit")

			c.JSON(http.StatusRequestEntityTooLarge, models.ErrorResponse{
				Success:   false,
				Error:     "Payload Too Large",
				Detail:    "URL length exceeds maximum allowed",
				Code:      "URL_TOO_LONG",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		// Check query string length (Requirement 4.3)
		queryLength := len(c.Request.URL.RawQuery)
		if queryLength > cfg.MaxQueryLength {
			logger.WithFields(logrus.Fields{
				"client_ip":    clientIP,
				"query_length": queryLength,
				"max_length":   cfg.MaxQueryLength,
				"path":         c.Request.URL.Path,
			}).Warn("Request query string exceeds size limit")

			c.JSON(http.StatusRequestEntityTooLarge, models.ErrorResponse{
				Success:   false,
				Error:     "Payload Too Large",
				Detail:    "Query string length exceeds maximum allowed",
				Code:      "QUERY_TOO_LONG",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		// Check total header size (Requirement 4.4)
		totalHeaderSize := 0
		for name, values := range c.Request.Header {
			totalHeaderSize += len(name)
			for _, v := range values {
				totalHeaderSize += len(v)
			}
		}
		if totalHeaderSize > cfg.MaxHeaderSize {
			logger.WithFields(logrus.Fields{
				"client_ip":   clientIP,
				"header_size": totalHeaderSize,
				"max_size":    cfg.MaxHeaderSize,
				"path":        c.Request.URL.Path,
			}).Warn("Request headers exceed size limit")

			c.JSON(http.StatusRequestEntityTooLarge, models.ErrorResponse{
				Success:   false,
				Error:     "Payload Too Large",
				Detail:    "Request headers exceed maximum allowed size",
				Code:      "HEADERS_TOO_LARGE",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		// For POST/PUT requests, limit body size (Requirement 4.1)
		if c.Request.Method == "POST" || c.Request.Method == "PUT" || c.Request.Method == "PATCH" {
			if c.Request.ContentLength > cfg.MaxRequestBodySize {
				logger.WithFields(logrus.Fields{
					"client_ip":      clientIP,
					"content_length": c.Request.ContentLength,
					"max_size":       cfg.MaxRequestBodySize,
					"path":           c.Request.URL.Path,
				}).Warn("Request body exceeds size limit")

				c.JSON(http.StatusRequestEntityTooLarge, models.ErrorResponse{
					Success:   false,
					Error:     "Payload Too Large",
					Detail:    "Request body exceeds maximum allowed size",
					Code:      "BODY_TOO_LARGE",
					Timestamp: time.Now(),
				})
				c.Abort()
				return
			}

			// Wrap the body reader to enforce limit
			c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, cfg.MaxRequestBodySize)
		}

		c.Next()
	}
}


// IPAccessControlMiddleware checks IP against allowlist and blocklist.
// This middleware should execute before all other processing.
// Requirements: 5.1, 5.2, 5.3, 5.4, 5.8
func IPAccessControlMiddleware(controller *CIDRAccessController, logger *logrus.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Skip if IP control is not enabled
		if controller == nil || !controller.IsEnabled() {
			c.Next()
			return
		}

		// Get client IP from headers or remote address
		clientIP := GetClientIP(c.Request.Header, c.Request.RemoteAddr)
		if clientIP == "" {
			clientIP = c.ClientIP()
		}

		// Check blocklist first (deny takes precedence)
		if controller.IsBlocked(clientIP) {
			logger.WithFields(logrus.Fields{
				"client_ip": clientIP,
				"path":      c.Request.URL.Path,
				"reason":    "blocklist",
			}).Warn("IP access denied: blocked")

			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Success:   false,
				Error:     "Forbidden",
				Detail:    "Access denied",
				Code:      "IP_BLOCKED",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		// Check allowlist (if configured)
		if !controller.IsAllowed(clientIP) {
			logger.WithFields(logrus.Fields{
				"client_ip": clientIP,
				"path":      c.Request.URL.Path,
				"reason":    "not_in_allowlist",
			}).Warn("IP access denied: not in allowlist")

			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Success:   false,
				Error:     "Forbidden",
				Detail:    "Access denied",
				Code:      "IP_NOT_ALLOWED",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}
