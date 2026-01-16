package api

import (
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"video-streaming-api/internal/config"

	"github.com/gin-gonic/gin"
	"github.com/leanovate/gopter"
	"github.com/leanovate/gopter/gen"
	"github.com/leanovate/gopter/prop"
)

// Feature: api-security-enhancements, Property 8: All required security headers are present
// For any HTTP response from the API, the response should contain all required security headers:
// Content-Security-Policy, Strict-Transport-Security (if HSTS enabled), Referrer-Policy,
// Permissions-Policy, X-Content-Type-Options, X-Frame-Options, and X-XSS-Protection.
// Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
func TestProperty8_AllRequiredSecurityHeadersArePresent(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)

	// Property: All required headers are present when HSTS is enabled
	properties.Property("all required headers present with HSTS enabled", prop.ForAll(
		func(csp, referrer, permissions string) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        31536000,
				CSPDirectives:     csp,
				ReferrerPolicy:    referrer,
				PermissionsPolicy: permissions,
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			headers := w.Header()

			// Check all required headers
			hasCSP := headers.Get("Content-Security-Policy") == csp
			hasHSTS := strings.Contains(headers.Get("Strict-Transport-Security"), "max-age=")
			hasReferrer := headers.Get("Referrer-Policy") == referrer
			hasPermissions := headers.Get("Permissions-Policy") == permissions
			hasXCTO := headers.Get("X-Content-Type-Options") == "nosniff"
			hasXFO := headers.Get("X-Frame-Options") == "DENY"
			hasXXSS := headers.Get("X-XSS-Protection") == "1; mode=block"

			return hasCSP && hasHSTS && hasReferrer && hasPermissions && hasXCTO && hasXFO && hasXXSS
		},
		gen.OneConstOf("default-src 'self'", "default-src 'self'; script-src 'self'"),
		gen.OneConstOf("strict-origin-when-cross-origin", "no-referrer", "same-origin"),
		gen.OneConstOf("geolocation=(), microphone=(), camera=()", "geolocation=()"),
	))

	// Property: HSTS header is absent when disabled
	properties.Property("HSTS header absent when disabled", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        false,
				HSTSMaxAge:        31536000,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			// HSTS should NOT be present
			return w.Header().Get("Strict-Transport-Security") == ""
		},
		gen.Int(),
	))

	// Property: X-Content-Type-Options is always nosniff
	properties.Property("X-Content-Type-Options is always nosniff", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        31536000,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Header().Get("X-Content-Type-Options") == "nosniff"
		},
		gen.Int(),
	))

	// Property: X-Frame-Options is always DENY
	properties.Property("X-Frame-Options is always DENY", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        31536000,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Header().Get("X-Frame-Options") == "DENY"
		},
		gen.Int(),
	))

	// Property: X-XSS-Protection is always set correctly
	properties.Property("X-XSS-Protection is always set correctly", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        31536000,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Header().Get("X-XSS-Protection") == "1; mode=block"
		},
		gen.Int(),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 9: HSTS max-age meets minimum requirement
// For any HTTP response when HSTS is enabled, the Strict-Transport-Security header
// should have a max-age value of at least 31536000 seconds.
// Validates: Requirements 3.2
func TestProperty9_HSTSMaxAgeMeetsMinimumRequirement(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)

	// Property: HSTS max-age is at least 31536000 when enabled
	properties.Property("HSTS max-age is at least minimum when enabled", prop.ForAll(
		func(maxAge int) bool {
			// Only test valid max-age values (>= minimum)
			if maxAge < 31536000 {
				maxAge = 31536000
			}

			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        maxAge,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			hstsHeader := w.Header().Get("Strict-Transport-Security")
			// Extract max-age value
			if !strings.Contains(hstsHeader, "max-age=") {
				return false
			}

			// Parse max-age value
			parts := strings.Split(hstsHeader, ";")
			for _, part := range parts {
				part = strings.TrimSpace(part)
				if strings.HasPrefix(part, "max-age=") {
					ageStr := strings.TrimPrefix(part, "max-age=")
					age, err := strconv.Atoi(ageStr)
					if err != nil {
						return false
					}
					return age >= 31536000
				}
			}
			return false
		},
		gen.IntRange(31536000, 63072000), // 1-2 years
	))

	// Property: HSTS includes includeSubDomains directive
	properties.Property("HSTS includes includeSubDomains", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        31536000,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			hstsHeader := w.Header().Get("Strict-Transport-Security")
			return strings.Contains(hstsHeader, "includeSubDomains")
		},
		gen.Int(),
	))

	// Property: HSTS includes preload directive
	properties.Property("HSTS includes preload directive", prop.ForAll(
		func(_ int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        31536000,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			hstsHeader := w.Header().Get("Strict-Transport-Security")
			return strings.Contains(hstsHeader, "preload")
		},
		gen.Int(),
	))

	// Property: Configured max-age is used in header
	properties.Property("configured max-age is used in header", prop.ForAll(
		func(maxAge int) bool {
			cfg := &config.SecurityConfig{
				EnableHSTS:        true,
				HSTSMaxAge:        maxAge,
				CSPDirectives:     "default-src 'self'",
				ReferrerPolicy:    "strict-origin-when-cross-origin",
				PermissionsPolicy: "geolocation=()",
			}

			router := gin.New()
			router.Use(EnhancedSecurityHeadersMiddleware(cfg))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			hstsHeader := w.Header().Get("Strict-Transport-Security")
			expectedPrefix := "max-age=" + strconv.Itoa(maxAge)
			return strings.Contains(hstsHeader, expectedPrefix)
		},
		gen.IntRange(31536000, 63072000),
	))

	properties.TestingRun(t)
}
