package api

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/leanovate/gopter"
	"github.com/leanovate/gopter/gen"
	"github.com/leanovate/gopter/prop"
	"github.com/sirupsen/logrus"
)

// Feature: api-security-enhancements, Property 27: Generic error messages to clients
// For any error response to clients, the error message should be generic and not contain
// internal implementation details, file paths, stack traces, database details, or service names.
// Validates: Requirements 8.1, 8.3, 8.4, 8.5, 8.6
func TestProperty27_GenericErrorMessagesToClients(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)

	// Property: Error responses don't contain file paths
	properties.Property("error responses don't contain file paths", prop.ForAll(
		func(statusCode int) bool {
			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)

			// Create an error with file path
			internalErr := errors.New("error at /home/user/app/internal/api/handlers.go:123")
			handler.SecureErrorResponse(c, statusCode, internalErr, "test")

			body := w.Body.String()
			return !strings.Contains(body, "/home/") &&
				!strings.Contains(body, ".go:") &&
				!strings.Contains(body, "handlers.go")
		},
		gen.IntRange(400, 599),
	))

	// Property: Error responses don't contain stack traces
	properties.Property("error responses don't contain stack traces", prop.ForAll(
		func(statusCode int) bool {
			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)

			// Create an error with stack trace pattern
			internalErr := errors.New("goroutine 1 [running]: main.main() at main.go:10")
			handler.SecureErrorResponse(c, statusCode, internalErr, "test")

			body := w.Body.String()
			return !strings.Contains(body, "goroutine") &&
				!strings.Contains(body, "[running]")
		},
		gen.IntRange(400, 599),
	))

	// Property: Error responses don't contain database connection strings
	properties.Property("error responses don't contain database connection strings", prop.ForAll(
		func(statusCode int) bool {
			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)

			// Create an error with database connection string
			internalErr := errors.New("connection failed: postgres://user:password@localhost:5432/db")
			handler.SecureErrorResponse(c, statusCode, internalErr, "test")

			body := w.Body.String()
			return !strings.Contains(body, "postgres://") &&
				!strings.Contains(body, "password@")
		},
		gen.IntRange(400, 599),
	))

	// Property: Error responses don't contain internal service names
	properties.Property("error responses don't contain internal service names", prop.ForAll(
		func(statusCode int) bool {
			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)

			// Create an error with internal service name
			internalErr := errors.New("internal_service failed: backend_server connection refused")
			handler.SecureErrorResponse(c, statusCode, internalErr, "test")

			body := w.Body.String()
			return !strings.Contains(body, "internal_service") &&
				!strings.Contains(body, "backend_server")
		},
		gen.IntRange(400, 599),
	))

	// Property: Error responses contain generic messages
	properties.Property("error responses contain generic messages", prop.ForAll(
		func(statusCode int) bool {
			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)

			internalErr := errors.New("detailed internal error with sensitive info")
			handler.SecureErrorResponse(c, statusCode, internalErr, "test")

			body := w.Body.String()
			// Should contain a generic error message
			return strings.Contains(body, `"success":false`) &&
				strings.Contains(body, `"error":`)
		},
		gen.IntRange(400, 599),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 28: Detailed errors logged internally
// For any error that occurs, the internal logs should contain detailed error information
// including error type, stack trace (if applicable), and context information.
// Validates: Requirements 8.2
func TestProperty28_DetailedErrorsLoggedInternally(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)

	// Property: Internal logs contain error details
	properties.Property("internal logs contain error details", prop.ForAll(
		func(statusCode int, errorMsg string) bool {
			if errorMsg == "" {
				errorMsg = "test error"
			}

			// Create a logger that writes to a buffer
			var logBuffer strings.Builder
			logger := logrus.New()
			logger.SetOutput(&logBuffer)
			logger.SetLevel(logrus.DebugLevel)
			logger.SetFormatter(&logrus.TextFormatter{DisableTimestamp: true})

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test/path", nil)
			c.Set("request_id", "test-request-123")

			internalErr := errors.New(errorMsg)
			handler.SecureErrorResponse(c, statusCode, internalErr, "test_context")

			logOutput := logBuffer.String()

			// Log should contain error details
			return strings.Contains(logOutput, errorMsg) &&
				strings.Contains(logOutput, "test_context") &&
				strings.Contains(logOutput, "/test/path")
		},
		gen.IntRange(400, 599),
		gen.AlphaString(),
	))

	// Property: Internal logs contain request ID
	properties.Property("internal logs contain request ID", prop.ForAll(
		func(requestID string) bool {
			if requestID == "" {
				requestID = "default-id"
			}

			var logBuffer strings.Builder
			logger := logrus.New()
			logger.SetOutput(&logBuffer)
			logger.SetLevel(logrus.DebugLevel)
			logger.SetFormatter(&logrus.TextFormatter{DisableTimestamp: true})

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)
			c.Set("request_id", requestID)

			handler.SecureErrorResponse(c, http.StatusInternalServerError, errors.New("test"), "ctx")

			logOutput := logBuffer.String()
			return strings.Contains(logOutput, requestID)
		},
		gen.AlphaString().SuchThat(func(s string) bool { return len(s) > 0 && len(s) < 50 }),
	))

	// Property: Internal logs contain client IP
	properties.Property("internal logs contain client IP", prop.ForAll(
		func(_ int) bool {
			var logBuffer strings.Builder
			logger := logrus.New()
			logger.SetOutput(&logBuffer)
			logger.SetLevel(logrus.DebugLevel)
			logger.SetFormatter(&logrus.TextFormatter{DisableTimestamp: true})

			handler := NewSecureErrorHandler(logger, false)

			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest("GET", "/test", nil)
			c.Request.RemoteAddr = "192.168.1.100:12345"

			handler.SecureErrorResponse(c, http.StatusInternalServerError, errors.New("test"), "ctx")

			logOutput := logBuffer.String()
			return strings.Contains(logOutput, "192.168.1.100")
		},
		gen.Int(),
	))

	properties.TestingRun(t)
}

// Feature: api-security-enhancements, Property 24: Sensitive data not logged
// For any log entry (application or audit), it should not contain sensitive configuration
// values such as passwords, tokens, or API keys.
// Validates: Requirements 7.3
func TestProperty24_SensitiveDataNotLogged(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	// Property: Passwords are detected as sensitive
	properties.Property("passwords are detected as sensitive", prop.ForAll(
		func(password string) bool {
			if password == "" {
				password = "secret123"
			}
			testString := "connection failed: password=" + password
			return ContainsSensitiveData(testString)
		},
		gen.AlphaString(),
	))

	// Property: Tokens are detected as sensitive
	properties.Property("tokens are detected as sensitive", prop.ForAll(
		func(token string) bool {
			if token == "" {
				token = "abc123token"
			}
			testString := "auth failed: token=" + token
			return ContainsSensitiveData(testString)
		},
		gen.AlphaString(),
	))

	// Property: API keys are detected as sensitive
	properties.Property("API keys are detected as sensitive", prop.ForAll(
		func(apiKey string) bool {
			if apiKey == "" {
				apiKey = "key123"
			}
			testString := "request failed: api_key=" + apiKey
			return ContainsSensitiveData(testString)
		},
		gen.AlphaString(),
	))

	// Property: File paths are detected as sensitive
	properties.Property("file paths are detected as sensitive", prop.ForAll(
		func(filename string) bool {
			if filename == "" || len(filename) < 3 {
				filename = "handler"
			}
			testString := "/home/user/app/" + filename + ".go"
			return ContainsSensitiveData(testString)
		},
		gen.AlphaString(),
	))

	// Property: Database connection strings are detected as sensitive
	properties.Property("database connection strings are detected as sensitive", prop.ForAll(
		func(_ int) bool {
			testStrings := []string{
				"postgres://user:pass@localhost:5432/db",
				"mysql://root:password@127.0.0.1:3306/mydb",
				"mongodb://admin:secret@localhost:27017/test",
				"redis://default:mypassword@localhost:6379",
			}
			for _, s := range testStrings {
				if !ContainsSensitiveData(s) {
					return false
				}
			}
			return true
		},
		gen.Int(),
	))

	// Property: Sensitive data is stripped from messages
	properties.Property("sensitive data is stripped from messages", prop.ForAll(
		func(_ int) bool {
			sensitiveMessage := "error at /home/user/app/main.go:42 with password=secret123"
			stripped := StripSensitiveData(sensitiveMessage)

			return !strings.Contains(stripped, "/home/user") &&
				!strings.Contains(stripped, "main.go") &&
				!strings.Contains(stripped, "password=secret123")
		},
		gen.Int(),
	))

	// Property: Generic messages pass the check
	properties.Property("generic messages pass the check", prop.ForAll(
		func(msgIndex int) bool {
			genericMessages := []string{
				"Invalid request",
				"Resource not found",
				"Internal server error",
				"Access denied",
				"Authentication required",
				"Request too large",
				"Method not allowed",
				"Service temporarily unavailable",
			}
			// Use the index to select a message (modulo to stay in bounds)
			idx := msgIndex % len(genericMessages)
			if idx < 0 {
				idx = -idx
			}
			msg := genericMessages[idx]
			return IsGenericMessage(msg)
		},
		gen.IntRange(0, 100),
	))

	properties.TestingRun(t)
}

// TestSecureRecoveryMiddleware tests the secure recovery middleware
func TestSecureRecoveryMiddleware(t *testing.T) {
	gin.SetMode(gin.TestMode)

	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	handler := NewSecureErrorHandler(logger, false)

	router := gin.New()
	router.Use(SecureRecoveryMiddleware(handler))
	router.GET("/panic", func(c *gin.Context) {
		panic("test panic")
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/panic", nil)
	router.ServeHTTP(w, req)

	// Should return 500 with generic message
	if w.Code != http.StatusInternalServerError {
		t.Errorf("expected status 500, got %d", w.Code)
	}

	body := w.Body.String()
	if !strings.Contains(body, "Internal server error") {
		t.Errorf("expected generic error message, got: %s", body)
	}

	// Should not contain panic details
	if strings.Contains(body, "test panic") {
		t.Errorf("response should not contain panic details")
	}
}
