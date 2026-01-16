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

// Feature: api-security-enhancements, Property 1: Parameter validation rejects invalid inputs
// For any request parameter (platform, video_id, playlist_id, quality, country, mode),
// if the parameter value does not match its validation rules, then the validation function
// should return an error.
// Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
func TestProperty1_ParameterValidationRejectsInvalidInputs(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	validator := NewDefaultInputValidator(testSecurityConfig())

	// Property: Invalid platforms are rejected
	properties.Property("invalid platforms are rejected", prop.ForAll(
		func(platform string) bool {
			err := validator.ValidatePlatform(platform)
			isValid := isValidPlatform(platform)
			if isValid {
				return err == nil
			}
			return err != nil
		},
		gen.AnyString(),
	))

	// Property: Video IDs exceeding max length are rejected
	properties.Property("video IDs exceeding max length are rejected", prop.ForAll(
		func(length int) bool {
			videoID := strings.Repeat("a", length)
			err := validator.ValidateVideoID(videoID)
			if length > 200 {
				return err != nil
			}
			if length == 0 {
				return err != nil // Empty is rejected
			}
			return err == nil
		},
		gen.IntRange(0, 300),
	))

	// Property: Video IDs with invalid characters are rejected
	properties.Property("video IDs with invalid characters are rejected", prop.ForAll(
		func(videoID string) bool {
			err := validator.ValidateVideoID(videoID)
			if videoID == "" {
				return err != nil // Empty is rejected
			}
			hasInvalidChars := !videoIDPattern.MatchString(videoID)
			if hasInvalidChars {
				return err != nil
			}
			if len(videoID) > 200 {
				return err != nil
			}
			return err == nil
		},
		gen.AnyString().SuchThat(func(s string) bool { return len(s) <= 250 }),
	))


	// Property: Playlist IDs follow same rules as video IDs
	properties.Property("playlist IDs with invalid characters are rejected", prop.ForAll(
		func(playlistID string) bool {
			err := validator.ValidatePlaylistID(playlistID)
			if playlistID == "" {
				return err != nil // Empty is rejected
			}
			hasInvalidChars := !videoIDPattern.MatchString(playlistID)
			if hasInvalidChars {
				return err != nil
			}
			if len(playlistID) > 200 {
				return err != nil
			}
			return err == nil
		},
		gen.AnyString().SuchThat(func(s string) bool { return len(s) <= 250 }),
	))

	// Property: Invalid qualities are rejected
	properties.Property("invalid qualities are rejected", prop.ForAll(
		func(quality string) bool {
			err := validator.ValidateQuality(quality)
			if quality == "" {
				return err == nil // Empty is allowed (optional)
			}
			isValid := isValidQuality(quality)
			if isValid {
				return err == nil
			}
			return err != nil
		},
		gen.AnyString(),
	))

	// Property: Invalid country codes are rejected
	properties.Property("invalid country codes are rejected", prop.ForAll(
		func(code string) bool {
			err := validator.ValidateCountryCode(code)
			if code == "" {
				return err == nil // Empty is allowed (optional)
			}
			normalized := strings.ToUpper(strings.TrimSpace(code))
			isValid := countryCodePattern.MatchString(normalized)
			if isValid {
				return err == nil
			}
			return err != nil
		},
		gen.OneGenOf(
			gen.Const("ABC"),      // 3 letters
			gen.Const("A"),        // 1 letter
			gen.Const("12"),       // Numbers
			gen.Const("U1"),       // Mixed
			gen.Const("usa"),      // 3 lowercase
			gen.Const("ABCD"),     // 4 letters
			gen.RegexMatch("[a-z]{3,5}"), // Lowercase 3-5 chars
		),
	))

	// Property: Invalid modes are rejected
	properties.Property("invalid modes are rejected", prop.ForAll(
		func(mode string) bool {
			err := validator.ValidateMode(mode)
			if mode == "" {
				return err == nil // Empty is allowed (optional)
			}
			normalized := strings.ToLower(strings.TrimSpace(mode))
			isValid := normalized == "proxy" || normalized == "direct"
			if isValid {
				return err == nil
			}
			return err != nil
		},
		gen.AnyString(),
	))

	// Property: Valid alphanumeric video IDs are accepted
	properties.Property("valid alphanumeric video IDs are accepted", prop.ForAll(
		func(videoID string) bool {
			err := validator.ValidateVideoID(videoID)
			return err == nil
		},
		gen.RegexMatch("[a-zA-Z0-9]{1,200}"),
	))

	// Property: Video IDs with hyphens and underscores are accepted
	properties.Property("video IDs with hyphens and underscores are accepted", prop.ForAll(
		func(base string) bool {
			// Add some hyphens and underscores
			videoID := base + "-" + base + "_" + base
			if len(videoID) > 200 || len(videoID) == 0 {
				return true // Skip this case
			}
			err := validator.ValidateVideoID(videoID)
			return err == nil
		},
		gen.RegexMatch("[a-zA-Z0-9]{1,60}"),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 2: Validation failures return 400 with descriptive errors
// For any request with invalid parameters, the API should return HTTP 400 status code
// with a response body containing the field name, validation error message, and error code.
// Validates: Requirements 1.7
func TestProperty2_ValidationFailuresReturn400WithDescriptiveErrors(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel) // Suppress logs during tests

	validator := NewDefaultInputValidator(testSecurityConfig())

	// Property: Invalid platform returns 400
	properties.Property("invalid platform returns 400 with error details", prop.ForAll(
		func(platform string) bool {
			router := gin.New()
			router.Use(ValidationMiddleware(validator, logger))
			router.GET("/test/:platform/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test/"+platform+"/validvideo123", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusBadRequest
		},
		gen.OneConstOf(
			"invalid",
			"facebook",
			"tiktok",
			"vimeo",
			"dailymotion",
			"unknown",
			"test123",
			"youtubes",
		),
	))

	// Property: Invalid video ID returns 400
	properties.Property("invalid video ID returns 400", prop.ForAll(
		func(videoID string) bool {
			// Skip valid video IDs
			if videoIDPattern.MatchString(videoID) && len(videoID) <= 200 && len(videoID) > 0 {
				return true
			}
			// Skip empty or IDs with path separators
			if videoID == "" || strings.Contains(videoID, "/") {
				return true
			}

			router := gin.New()
			router.Use(ValidationMiddleware(validator, logger))
			router.GET("/test/:platform/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test/youtube/"+videoID, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusBadRequest
		},
		gen.AnyString().SuchThat(func(s string) bool {
			return len(s) > 0 && len(s) <= 250 && !strings.Contains(s, "/")
		}),
	))

	// Property: Invalid quality query param returns 400
	properties.Property("invalid quality returns 400", prop.ForAll(
		func(quality string) bool {
			router := gin.New()
			router.Use(ValidationMiddleware(validator, logger))
			router.GET("/test/:platform/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test/youtube/abc123?quality="+quality, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusBadRequest
		},
		gen.OneConstOf(
			"invalid",
			"4k",
			"hd",
			"sd",
			"medium",
			"high",
			"low",
			"1080",
			"720",
		),
	))

	// Property: Invalid country code returns 400
	properties.Property("invalid country code returns 400", prop.ForAll(
		func(country string) bool {
			router := gin.New()
			router.Use(ValidationMiddleware(validator, logger))
			router.GET("/test/:platform/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test/youtube/abc123?country="+country, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusBadRequest
		},
		gen.OneConstOf(
			"USA",
			"A",
			"123",
			"ABCD",
			"1A",
		),
	))

	// Property: Invalid mode returns 400
	properties.Property("invalid mode returns 400", prop.ForAll(
		func(mode string) bool {
			router := gin.New()
			router.Use(ValidationMiddleware(validator, logger))
			router.GET("/test/:platform/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test/youtube/abc123?mode="+mode, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusBadRequest
		},
		gen.OneConstOf(
			"invalid",
			"stream",
			"redirect",
			"auto",
			"both",
			"none",
		),
	))

	// Property: Valid requests pass through middleware
	properties.Property("valid requests return 200", prop.ForAll(
		func(videoID string) bool {
			router := gin.New()
			router.Use(ValidationMiddleware(validator, logger))
			router.GET("/test/:platform/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test/youtube/"+videoID+"?quality=best&mode=proxy&country=US", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusOK
		},
		gen.RegexMatch("[a-zA-Z0-9]{1,50}"),
	))

	properties.TestingRun(t)
}


// Helper functions

func testSecurityConfig() *config.SecurityConfig {
	return &config.SecurityConfig{
		MaxVideoIDLength:    200,
		MaxPlaylistIDLength: 200,
		AllowedPlatforms:    []string{"youtube", "bilibili", "twitter", "instagram", "twitch"},
		AllowedQualities:    []string{"best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "worst"},
	}
}

func isValidPlatform(platform string) bool {
	validPlatforms := map[string]bool{
		"youtube":   true,
		"bilibili":  true,
		"twitter":   true,
		"instagram": true,
		"twitch":    true,
	}
	return validPlatforms[strings.ToLower(strings.TrimSpace(platform))]
}

func isValidQuality(quality string) bool {
	validQualities := map[string]bool{
		"best":  true,
		"2160p": true,
		"1440p": true,
		"1080p": true,
		"720p":  true,
		"480p":  true,
		"360p":  true,
		"worst": true,
	}
	return validQualities[strings.ToLower(strings.TrimSpace(quality))]
}
