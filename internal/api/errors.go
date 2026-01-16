package api

import (
	"fmt"
	"net/http"
	"regexp"
	"strings"
	"time"

	"video-streaming-api/internal/models"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// SecureErrorHandler handles error responses securely
type SecureErrorHandler struct {
	logger               *logrus.Logger
	exposeDetailedErrors bool
}

// NewSecureErrorHandler creates a new secure error handler
func NewSecureErrorHandler(logger *logrus.Logger, exposeDetailedErrors bool) *SecureErrorHandler {
	return &SecureErrorHandler{
		logger:               logger,
		exposeDetailedErrors: exposeDetailedErrors,
	}
}

// SensitivePatterns contains patterns that should be stripped from error messages
var sensitivePatterns = []*regexp.Regexp{
	// File paths (Unix and Windows)
	regexp.MustCompile(`(?i)(/[a-z0-9_\-./]+)+\.(go|py|js|ts|java|rb|php|c|cpp|h)`),
	regexp.MustCompile(`(?i)([a-z]:\\[a-z0-9_\-\\]+)+\.(go|py|js|ts|java|rb|php|c|cpp|h)`),
	// Stack traces
	regexp.MustCompile(`(?i)goroutine \d+ \[.+\]:`),
	regexp.MustCompile(`(?i)at .+:\d+`),
	regexp.MustCompile(`(?i)\.go:\d+`),
	// Database connection strings
	regexp.MustCompile(`(?i)(postgres|mysql|mongodb|redis)://[^\s]+`),
	regexp.MustCompile(`(?i)host=\S+\s+port=\d+`),
	// IP addresses and ports (internal)
	regexp.MustCompile(`(?i)127\.0\.0\.1:\d+`),
	regexp.MustCompile(`(?i)localhost:\d+`),
	// Service names and internal endpoints
	regexp.MustCompile(`(?i)internal[_-]?service`),
	regexp.MustCompile(`(?i)backend[_-]?server`),
	// Passwords and tokens in error messages
	regexp.MustCompile(`(?i)password[=:]\S+`),
	regexp.MustCompile(`(?i)token[=:]\S+`),
	regexp.MustCompile(`(?i)api[_-]?key[=:]\S+`),
	regexp.MustCompile(`(?i)secret[=:]\S+`),
}

// GenericErrorMessages maps internal error types to generic client messages
var genericErrorMessages = map[int]string{
	http.StatusBadRequest:          "Invalid request",
	http.StatusUnauthorized:        "Authentication required",
	http.StatusForbidden:           "Access denied",
	http.StatusNotFound:            "Resource not found",
	http.StatusMethodNotAllowed:    "Method not allowed",
	http.StatusConflict:            "Request conflict",
	http.StatusRequestEntityTooLarge: "Request too large",
	http.StatusUnprocessableEntity: "Invalid request data",
	http.StatusTooManyRequests:     "Too many requests",
	http.StatusInternalServerError: "Internal server error",
	http.StatusBadGateway:          "Service temporarily unavailable",
	http.StatusServiceUnavailable:  "Service temporarily unavailable",
	http.StatusGatewayTimeout:      "Request timeout",
}

// SecureErrorResponse sends a secure error response to the client
// It returns generic messages to clients and logs detailed errors internally
func (h *SecureErrorHandler) SecureErrorResponse(c *gin.Context, statusCode int, internalError error, context string) {
	requestID := c.GetString("request_id")
	if requestID == "" {
		requestID = "unknown"
	}

	// Get generic message for client
	genericMessage := genericErrorMessages[statusCode]
	if genericMessage == "" {
		genericMessage = "An error occurred"
	}

	// Log detailed error internally
	h.logDetailedError(c, statusCode, internalError, context, requestID)

	// Build client response
	response := models.ErrorResponse{
		Success:   false,
		Error:     genericMessage,
		Code:      http.StatusText(statusCode),
		Timestamp: time.Now(),
	}

	// Only include detail in development mode
	if h.exposeDetailedErrors && internalError != nil {
		response.Detail = h.sanitizeErrorMessage(internalError.Error())
	}

	c.JSON(statusCode, response)
}


// SecureErrorResponseWithMessage sends a secure error response with a custom generic message
func (h *SecureErrorHandler) SecureErrorResponseWithMessage(c *gin.Context, statusCode int, genericMessage string, internalError error, context string) {
	requestID := c.GetString("request_id")
	if requestID == "" {
		requestID = "unknown"
	}

	// Log detailed error internally
	h.logDetailedError(c, statusCode, internalError, context, requestID)

	// Build client response with custom generic message
	response := models.ErrorResponse{
		Success:   false,
		Error:     genericMessage,
		Code:      http.StatusText(statusCode),
		Timestamp: time.Now(),
	}

	// Only include detail in development mode
	if h.exposeDetailedErrors && internalError != nil {
		response.Detail = h.sanitizeErrorMessage(internalError.Error())
	}

	c.JSON(statusCode, response)
}

// logDetailedError logs the full error details internally
func (h *SecureErrorHandler) logDetailedError(c *gin.Context, statusCode int, err error, context, requestID string) {
	if h.logger == nil {
		return
	}

	fields := logrus.Fields{
		"request_id":  requestID,
		"status_code": statusCode,
		"method":      c.Request.Method,
		"path":        c.Request.URL.Path,
		"client_ip":   c.ClientIP(),
		"user_agent":  c.Request.UserAgent(),
		"context":     context,
	}

	if err != nil {
		fields["error"] = err.Error()
		fields["error_type"] = fmt.Sprintf("%T", err)
	}

	// Log at appropriate level based on status code
	switch {
	case statusCode >= 500:
		h.logger.WithFields(fields).Error("Server error occurred")
	case statusCode >= 400:
		h.logger.WithFields(fields).Warn("Client error occurred")
	default:
		h.logger.WithFields(fields).Info("Error response sent")
	}
}

// sanitizeErrorMessage removes sensitive information from error messages
func (h *SecureErrorHandler) sanitizeErrorMessage(message string) string {
	sanitized := message

	// Apply all sensitive patterns
	for _, pattern := range sensitivePatterns {
		sanitized = pattern.ReplaceAllString(sanitized, "[REDACTED]")
	}

	return sanitized
}

// ContainsSensitiveData checks if a string contains sensitive data patterns
func ContainsSensitiveData(s string) bool {
	for _, pattern := range sensitivePatterns {
		if pattern.MatchString(s) {
			return true
		}
	}
	return false
}

// StripSensitiveData removes sensitive data from a string
func StripSensitiveData(s string) string {
	result := s
	for _, pattern := range sensitivePatterns {
		result = pattern.ReplaceAllString(result, "[REDACTED]")
	}
	return result
}

// IsGenericMessage checks if a message is generic (doesn't contain sensitive info)
func IsGenericMessage(message string) bool {
	// Check for common sensitive patterns
	sensitiveIndicators := []string{
		".go:",             // Go file references
		".py:",             // Python file references
		"goroutine",        // Stack traces
		"panic:",           // Panic messages
		"runtime error:",   // Runtime errors
		"sql:",             // SQL errors
		"connection refused", // Connection details
		"connection failed",  // Connection details
		"password=",        // Password references
		"password:",        // Password references
		"token=",           // Token references
		"token:",           // Token references
		"secret=",          // Secret references
		"secret:",          // Secret references
		"api_key=",         // API key references
		"apikey=",          // API key references
		"localhost:",       // Internal addresses with port
		"127.0.0.1:",       // Loopback addresses with port
		"internal_service", // Internal service names
		"internal-service", // Internal service names
		"backend_server",   // Backend references
		"backend-server",   // Backend references
		"/home/",           // Unix paths
		"/var/",            // Unix paths
		"/etc/",            // Unix paths
		"C:\\",             // Windows paths
		"D:\\",             // Windows paths
	}

	lowerMessage := strings.ToLower(message)
	for _, indicator := range sensitiveIndicators {
		if strings.Contains(lowerMessage, strings.ToLower(indicator)) {
			return false
		}
	}

	return true
}

// SecureRecoveryMiddleware creates a recovery middleware that uses secure error handling
func SecureRecoveryMiddleware(handler *SecureErrorHandler) gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				// Log the panic with full details internally
				if handler.logger != nil {
					handler.logger.WithFields(logrus.Fields{
						"panic":      fmt.Sprintf("%v", err),
						"request_id": c.GetString("request_id"),
						"method":     c.Request.Method,
						"path":       c.Request.URL.Path,
						"client_ip":  c.ClientIP(),
					}).Error("Panic recovered")
				}

				// Send generic error to client
				c.AbortWithStatusJSON(http.StatusInternalServerError, models.ErrorResponse{
					Success:   false,
					Error:     "Internal server error",
					Code:      http.StatusText(http.StatusInternalServerError),
					Timestamp: time.Now(),
				})
			}
		}()
		c.Next()
	}
}
