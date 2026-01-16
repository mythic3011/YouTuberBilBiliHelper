package api

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"video-streaming-api/internal/config"

	"github.com/gin-gonic/gin"
	"github.com/leanovate/gopter"
	"github.com/leanovate/gopter/gen"
	"github.com/leanovate/gopter/prop"
	"github.com/sirupsen/logrus"
)

// Feature: api-security-enhancements, Property 10: Size limits are enforced
// For any request, if the request body size exceeds MaxRequestBodySize, or URL length
// exceeds MaxURLLength, or query string length exceeds MaxQueryLength, or any header
// size exceeds MaxHeaderSize, then the API should reject the request before processing.
// Validates: Requirements 4.1, 4.2, 4.3, 4.4
func TestProperty10_SizeLimitsAreEnforced(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Property: URLs within limit are accepted
	properties.Property("URLs within limit are accepted", prop.ForAll(
		func(pathLen int) bool {
			cfg := &config.SecurityConfig{
				MaxURLLength:       2048,
				MaxQueryLength:     1024,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test/*path", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			// Create path within limit
			path := "/test/" + strings.Repeat("a", pathLen)
			req := httptest.NewRequest("GET", path, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusOK
		},
		gen.IntRange(1, 100), // Small paths well within limit
	))

	// Property: URLs exceeding limit are rejected
	properties.Property("URLs exceeding limit are rejected", prop.ForAll(
		func(excess int) bool {
			maxLen := 100 // Use small limit for testing
			cfg := &config.SecurityConfig{
				MaxURLLength:       maxLen,
				MaxQueryLength:     1024,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test/*path", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			// Create path exceeding limit
			path := "/test/" + strings.Repeat("a", maxLen+excess)
			req := httptest.NewRequest("GET", path, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusRequestEntityTooLarge
		},
		gen.IntRange(10, 100),
	))

	// Property: Query strings within limit are accepted
	properties.Property("query strings within limit are accepted", prop.ForAll(
		func(queryLen int) bool {
			cfg := &config.SecurityConfig{
				MaxURLLength:       2048,
				MaxQueryLength:     1024,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			// Create query within limit
			query := "param=" + strings.Repeat("a", queryLen)
			req := httptest.NewRequest("GET", "/test?"+query, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusOK
		},
		gen.IntRange(1, 100), // Small queries well within limit
	))

	// Property: Query strings exceeding limit are rejected
	properties.Property("query strings exceeding limit are rejected", prop.ForAll(
		func(excess int) bool {
			maxLen := 50 // Use small limit for testing
			cfg := &config.SecurityConfig{
				MaxURLLength:       4096, // Large enough to not trigger URL limit
				MaxQueryLength:     maxLen,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			// Create query exceeding limit
			query := "param=" + strings.Repeat("a", maxLen+excess)
			req := httptest.NewRequest("GET", "/test?"+query, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusRequestEntityTooLarge
		},
		gen.IntRange(10, 100),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 11: Size limit violations return 413
// For any request that exceeds any size limit, the API should return HTTP 413 status code.
// Validates: Requirements 4.5
func TestProperty11_SizeLimitViolationsReturn413(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Property: URL limit violation returns 413
	properties.Property("URL limit violation returns 413", prop.ForAll(
		func(excess int) bool {
			maxLen := 50
			cfg := &config.SecurityConfig{
				MaxURLLength:       maxLen,
				MaxQueryLength:     1024,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test/*path", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			path := "/test/" + strings.Repeat("x", maxLen+excess)
			req := httptest.NewRequest("GET", path, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusRequestEntityTooLarge
		},
		gen.IntRange(10, 50),
	))

	// Property: Query limit violation returns 413
	properties.Property("query limit violation returns 413", prop.ForAll(
		func(excess int) bool {
			maxLen := 30
			cfg := &config.SecurityConfig{
				MaxURLLength:       4096,
				MaxQueryLength:     maxLen,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			query := "q=" + strings.Repeat("y", maxLen+excess)
			req := httptest.NewRequest("GET", "/test?"+query, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusRequestEntityTooLarge
		},
		gen.IntRange(10, 50),
	))

	// Property: Header limit violation returns 413
	properties.Property("header limit violation returns 413", prop.ForAll(
		func(excess int) bool {
			maxSize := 100
			cfg := &config.SecurityConfig{
				MaxURLLength:       4096,
				MaxQueryLength:     1024,
				MaxHeaderSize:      maxSize,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			// Add large header
			req.Header.Set("X-Large-Header", strings.Repeat("z", maxSize+excess))
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusRequestEntityTooLarge
		},
		gen.IntRange(10, 50),
	))

	// Property: Requests within all limits return 200
	properties.Property("requests within all limits return 200", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				MaxURLLength:       2048,
				MaxQueryLength:     1024,
				MaxHeaderSize:      8192,
				MaxRequestBodySize: 1048576,
			}

			router := gin.New()
			router.Use(RequestSizeLimitMiddleware(cfg, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test?param=value", nil)
			req.Header.Set("X-Custom", "small-value")
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusOK
		},
		gen.Int(),
	))

	properties.TestingRun(t)
}
