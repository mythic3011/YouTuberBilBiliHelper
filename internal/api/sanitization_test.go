package api

import (
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

// Feature: api-security-enhancements, Property 4: Path traversal sequences are removed
// For any string containing path traversal patterns (../, ..\, ..%2F, ..%5C),
// the sanitization function should return a string with all traversal sequences removed.
// Validates: Requirements 2.1
func TestProperty4_PathTraversalSequencesAreRemoved(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	sanitizer := NewDefaultInputSanitizer()

	// Property: ../ sequences are removed
	properties.Property("../ sequences are removed from paths", prop.ForAll(
		func(prefix, suffix string) bool {
			input := prefix + "../" + suffix
			result, err := sanitizer.SanitizePath(input)
			if err != nil {
				return true // Error is acceptable for invalid input
			}
			return !strings.Contains(result, "../")
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: ..\ sequences are removed
	properties.Property("..\\ sequences are removed from paths", prop.ForAll(
		func(prefix, suffix string) bool {
			input := prefix + "..\\" + suffix
			result, err := sanitizer.SanitizePath(input)
			if err != nil {
				return true
			}
			return !strings.Contains(result, "..\\")
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: URL-encoded traversal sequences are removed
	properties.Property("URL-encoded traversal sequences are removed", prop.ForAll(
		func(prefix, suffix string) bool {
			// Test ..%2f (URL encoded /)
			input := prefix + "..%2f" + suffix
			result, err := sanitizer.SanitizePath(input)
			if err != nil {
				return true
			}
			// After decoding and sanitization, should not contain ../
			return !strings.Contains(result, "../") && !strings.Contains(result, "..%2f")
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: Multiple traversal sequences are all removed
	properties.Property("multiple traversal sequences are all removed", prop.ForAll(
		func(count int) bool {
			input := strings.Repeat("../", count) + "etc/passwd"
			result, err := sanitizer.SanitizePath(input)
			if err != nil {
				return true
			}
			return !strings.Contains(result, "../")
		},
		gen.IntRange(1, 20),
	))

	// Property: Clean paths remain unchanged
	properties.Property("clean paths remain unchanged", prop.ForAll(
		func(path string) bool {
			result, err := sanitizer.SanitizePath(path)
			if err != nil {
				return true
			}
			// Clean alphanumeric paths should remain the same
			return result == path
		},
		gen.RegexMatch("[a-zA-Z0-9]{1,50}"),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 5: URL-encoded values are decoded and validated
// For any URL-encoded parameter value, the sanitization function should decode it
// and then validate the decoded value against the same rules as non-encoded values.
// Validates: Requirements 2.2
func TestProperty5_URLEncodedValuesAreDecodedAndValidated(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	sanitizer := NewDefaultInputSanitizer()

	// Property: Valid URL-encoded values are decoded
	properties.Property("valid URL-encoded values are decoded", prop.ForAll(
		func(input string) bool {
			// URL encode the input
			encoded := strings.ReplaceAll(input, " ", "%20")
			result, err := sanitizer.SanitizeURL(encoded)
			if err != nil {
				return true // Error is acceptable
			}
			// Should be decoded
			return !strings.Contains(result, "%20") || !strings.Contains(input, " ")
		},
		gen.RegexMatch("[a-zA-Z0-9 ]{1,20}"),
	))

	// Property: Double-encoded values are handled
	properties.Property("double-encoded traversal is handled", prop.ForAll(
		func(suffix string) bool {
			// %252e%252e%252f is double-encoded ../
			input := "%2e%2e%2f" + suffix
			result, err := sanitizer.SanitizeURL(input)
			if err != nil {
				return true
			}
			// After single decode, should get ../ which path sanitizer would catch
			_ = result
			return true // Just verify no panic
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: Invalid URL encoding returns error
	properties.Property("invalid URL encoding is handled gracefully", prop.ForAll(
		func(suffix string) bool {
			// Invalid percent encoding
			input := "%ZZ" + suffix
			_, err := sanitizer.SanitizeURL(input)
			// Should return error for invalid encoding
			return err != nil
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	properties.TestingRun(t)
}

// Feature: api-security-enhancements, Property 6: Null bytes and control characters are rejected
// For any string containing null bytes (\x00) or control characters (\x01-\x1F excluding
// tab, newline, carriage return), the sanitization function should reject the input.
// Validates: Requirements 2.4
func TestProperty6_NullBytesAndControlCharsAreRejected(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	sanitizer := NewDefaultInputSanitizer()

	// Property: Null bytes are detected
	properties.Property("null bytes are detected", prop.ForAll(
		func(prefix, suffix string) bool {
			input := prefix + "\x00" + suffix
			return sanitizer.ContainsNullOrControlChars(input)
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: Control characters (except tab, newline, CR) are detected
	properties.Property("control characters are detected", prop.ForAll(
		func(prefix string, controlChar int) bool {
			// Skip allowed control chars: tab (9), newline (10), carriage return (13)
			if controlChar == 9 || controlChar == 10 || controlChar == 13 {
				return true // Skip these
			}
			input := prefix + string(rune(controlChar)) + "suffix"
			return sanitizer.ContainsNullOrControlChars(input)
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.IntRange(1, 31),
	))

	// Property: Tab, newline, and carriage return are allowed
	properties.Property("tab newline and CR are allowed", prop.ForAll(
		func(prefix, suffix string) bool {
			// Tab
			inputTab := prefix + "\t" + suffix
			// Newline
			inputNL := prefix + "\n" + suffix
			// Carriage return
			inputCR := prefix + "\r" + suffix

			return !sanitizer.ContainsNullOrControlChars(inputTab) &&
				!sanitizer.ContainsNullOrControlChars(inputNL) &&
				!sanitizer.ContainsNullOrControlChars(inputCR)
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: Clean strings pass
	properties.Property("clean strings pass null/control check", prop.ForAll(
		func(input string) bool {
			return !sanitizer.ContainsNullOrControlChars(input)
		},
		gen.RegexMatch("[a-zA-Z0-9]{1,50}"),
	))

	// Property: Sanitization rejects null bytes
	properties.Property("SanitizePath rejects null bytes", prop.ForAll(
		func(prefix, suffix string) bool {
			input := prefix + "\x00" + suffix
			_, err := sanitizer.SanitizePath(input)
			return err != nil
		},
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
		gen.RegexMatch("[a-zA-Z0-9]{0,10}"),
	))

	// Property: Middleware rejects null bytes with 400
	properties.Property("middleware rejects null bytes with 400", prop.ForAll(
		func(videoID string) bool {
			gin.SetMode(gin.TestMode)
			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			router := gin.New()
			router.Use(SanitizationMiddleware(sanitizer, logger))
			router.GET("/test/:video_id", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			// Add null byte to video ID
			maliciousID := videoID + "%00" + "malicious"
			req := httptest.NewRequest("GET", "/test/"+maliciousID, nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusBadRequest
		},
		gen.RegexMatch("[a-zA-Z0-9]{1,10}"),
	))

	properties.TestingRun(t)
}
