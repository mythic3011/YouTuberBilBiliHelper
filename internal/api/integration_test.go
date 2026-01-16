package api

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"video-streaming-api/internal/config"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// TestSecurityMiddlewareStack tests the full security middleware stack integration
func TestSecurityMiddlewareStack(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create test configuration
	cfg := &config.SecurityConfig{
		MaxVideoIDLength:    200,
		MaxPlaylistIDLength: 200,
		AllowedPlatforms:    []string{"youtube", "bilibili", "twitter", "instagram", "twitch"},
		AllowedQualities:    []string{"best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "worst"},
		MaxRequestBodySize:  1048576,
		MaxURLLength:        2048,
		MaxQueryLength:      1024,
		MaxHeaderSize:       8192,
		EnableIPControl:     false,
		EnableHSTS:          true,
		HSTSMaxAge:          31536000,
		CSPDirectives:       "default-src 'self'",
		ReferrerPolicy:      "strict-origin-when-cross-origin",
		PermissionsPolicy:   "geolocation=(), microphone=(), camera=()",
	}

	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Create router with security middleware
	router := gin.New()

	// Apply middleware in correct order
	router.Use(RequestSizeLimitMiddleware(cfg, logger))

	validator := NewDefaultInputValidator(cfg)
	router.Use(ValidationMiddleware(validator, logger))

	sanitizer := NewDefaultInputSanitizer()
	router.Use(SanitizationMiddleware(sanitizer, logger))

	router.Use(EnhancedSecurityHeadersMiddleware(cfg))

	// Add test endpoint
	router.GET("/api/v2/videos/:platform/:video_id", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"success": true})
	})

	t.Run("valid request passes all middleware", func(t *testing.T) {
		w := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/api/v2/videos/youtube/dQw4w9WgXcQ?quality=1080p", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		// Check security headers are present
		if w.Header().Get("X-Content-Type-Options") != "nosniff" {
			t.Error("missing X-Content-Type-Options header")
		}
		if w.Header().Get("X-Frame-Options") != "DENY" {
			t.Error("missing X-Frame-Options header")
		}
		if !strings.Contains(w.Header().Get("Strict-Transport-Security"), "max-age=") {
			t.Error("missing HSTS header")
		}
	})

	t.Run("invalid platform is rejected", func(t *testing.T) {
		w := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/api/v2/videos/invalid_platform/abc123", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})

	t.Run("null bytes are rejected", func(t *testing.T) {
		w := httptest.NewRecorder()
		// Use URL-encoded null byte (%00) since raw null bytes can't be in URLs
		req := httptest.NewRequest("GET", "/api/v2/videos/youtube/abc%00123", nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})

	t.Run("URL too long is rejected", func(t *testing.T) {
		longID := strings.Repeat("a", 3000)
		w := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/api/v2/videos/youtube/"+longID, nil)
		router.ServeHTTP(w, req)

		if w.Code != http.StatusRequestEntityTooLarge {
			t.Errorf("expected status 413, got %d", w.Code)
		}
	})
}

// TestMiddlewareExecutionOrder verifies middleware executes in correct order
func TestMiddlewareExecutionOrder(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.SecurityConfig{
		MaxVideoIDLength:    200,
		MaxPlaylistIDLength: 200,
		AllowedPlatforms:    []string{"youtube"},
		AllowedQualities:    []string{"best"},
		MaxRequestBodySize:  1048576,
		MaxURLLength:        2048,
		MaxQueryLength:      1024,
		MaxHeaderSize:       8192,
		EnableIPControl:     true,
		IPBlocklist:         []string{"192.168.1.100/32"},
		EnableHSTS:          true,
		HSTSMaxAge:          31536000,
		CSPDirectives:       "default-src 'self'",
		ReferrerPolicy:      "strict-origin-when-cross-origin",
		PermissionsPolicy:   "geolocation=()",
	}

	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Create IP controller
	ipController, _ := NewCIDRAccessController(cfg.IPAllowlist, cfg.IPBlocklist, true)

	router := gin.New()

	// Apply middleware in correct order (IP first)
	router.Use(IPAccessControlMiddleware(ipController, logger))
	router.Use(RequestSizeLimitMiddleware(cfg, logger))

	validator := NewDefaultInputValidator(cfg)
	router.Use(ValidationMiddleware(validator, logger))

	router.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"success": true})
	})

	t.Run("blocked IP is rejected before other checks", func(t *testing.T) {
		w := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("X-Forwarded-For", "192.168.1.100")
		req.RemoteAddr = "192.168.1.100:12345"
		router.ServeHTTP(w, req)

		if w.Code != http.StatusForbidden {
			t.Errorf("expected status 403, got %d", w.Code)
		}
	})

	t.Run("allowed IP proceeds to next middleware", func(t *testing.T) {
		w := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("X-Forwarded-For", "10.0.0.1")
		req.RemoteAddr = "10.0.0.1:12345"
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}
	})
}

// TestSecurityHeadersPresence verifies all security headers are set
func TestSecurityHeadersPresence(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.SecurityConfig{
		EnableHSTS:        true,
		HSTSMaxAge:        31536000,
		CSPDirectives:     "default-src 'self'; script-src 'self'",
		ReferrerPolicy:    "strict-origin-when-cross-origin",
		PermissionsPolicy: "geolocation=(), microphone=(), camera=()",
	}

	router := gin.New()
	router.Use(EnhancedSecurityHeadersMiddleware(cfg))
	router.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"success": true})
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	router.ServeHTTP(w, req)

	expectedHeaders := map[string]string{
		"X-Content-Type-Options": "nosniff",
		"X-Frame-Options":        "DENY",
		"X-XSS-Protection":       "1; mode=block",
		"Content-Security-Policy": "default-src 'self'; script-src 'self'",
		"Referrer-Policy":        "strict-origin-when-cross-origin",
		"Permissions-Policy":     "geolocation=(), microphone=(), camera=()",
	}

	for header, expected := range expectedHeaders {
		actual := w.Header().Get(header)
		if actual != expected {
			t.Errorf("header %s: expected %q, got %q", header, expected, actual)
		}
	}

	// Check HSTS header contains max-age
	hsts := w.Header().Get("Strict-Transport-Security")
	if !strings.Contains(hsts, "max-age=31536000") {
		t.Errorf("HSTS header missing or incorrect: %s", hsts)
	}
}

// TestConfigurationLoading tests that security config loads correctly
func TestConfigurationLoading(t *testing.T) {
	cfg := config.Load()

	// Verify default values are set
	if cfg.Security.MaxVideoIDLength <= 0 {
		t.Error("MaxVideoIDLength should have a positive default")
	}
	if cfg.Security.MaxURLLength <= 0 {
		t.Error("MaxURLLength should have a positive default")
	}
	if len(cfg.Security.AllowedPlatforms) == 0 {
		t.Error("AllowedPlatforms should have defaults")
	}
	if len(cfg.Security.AllowedQualities) == 0 {
		t.Error("AllowedQualities should have defaults")
	}
	if cfg.Security.HSTSMaxAge < 31536000 {
		t.Error("HSTSMaxAge should be at least 31536000")
	}
}
