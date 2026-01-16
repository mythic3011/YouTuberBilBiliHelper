package config

import (
	"reflect"
	"strconv"
	"strings"
	"testing"

	"github.com/leanovate/gopter"
	"github.com/leanovate/gopter/gen"
	"github.com/leanovate/gopter/prop"
)

// Feature: api-security-enhancements, Property 22: Required configuration validation
// For any missing required configuration value, the API startup should fail with an error
// message identifying the missing configuration key.
// Validates: Requirements 7.1
func TestProperty22_RequiredConfigurationValidation(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 20

	properties := gopter.NewProperties(parameters)

	// Property: Empty allowed platforms should fail validation
	properties.Property("empty allowed platforms are rejected", prop.ForAll(
		func(platforms []string) bool {
			cfg := validSecurityConfig()
			cfg.AllowedPlatforms = platforms

			err := cfg.Validate()
			if len(platforms) == 0 {
				return err != nil && strings.Contains(err.Error(), "ALLOWED_PLATFORMS")
			}
			// Non-empty platforms should not cause this specific error
			return err == nil || !strings.Contains(err.Error(), "ALLOWED_PLATFORMS must not be empty")
		},
		gen.SliceOf(gen.AlphaString()).SuchThat(func(s []string) bool {
			// Filter out slices with empty strings
			for _, v := range s {
				if v == "" {
					return false
				}
			}
			return true
		}),
	))

	// Property: Empty allowed qualities should fail validation
	properties.Property("empty allowed qualities are rejected", prop.ForAll(
		func(qualities []string) bool {
			cfg := validSecurityConfig()
			cfg.AllowedQualities = qualities

			err := cfg.Validate()
			if len(qualities) == 0 {
				return err != nil && strings.Contains(err.Error(), "ALLOWED_QUALITIES")
			}
			return err == nil || !strings.Contains(err.Error(), "ALLOWED_QUALITIES must not be empty")
		},
		gen.SliceOf(gen.AlphaString()).SuchThat(func(s []string) bool {
			for _, v := range s {
				if v == "" {
					return false
				}
			}
			return true
		}),
	))

	// Property: Empty CSP directives should fail validation
	properties.Property("empty CSP directives are rejected", prop.ForAll(
		func(csp string) bool {
			cfg := validSecurityConfig()
			cfg.CSPDirectives = csp

			err := cfg.Validate()
			if csp == "" {
				return err != nil && strings.Contains(err.Error(), "CSP_DIRECTIVES")
			}
			return err == nil || !strings.Contains(err.Error(), "CSP_DIRECTIVES must not be empty")
		},
		gen.AnyString(),
	))

	// Property: Empty referrer policy should fail validation
	properties.Property("empty referrer policy is rejected", prop.ForAll(
		func(policy string) bool {
			cfg := validSecurityConfig()
			cfg.ReferrerPolicy = policy

			err := cfg.Validate()
			if policy == "" {
				return err != nil && strings.Contains(err.Error(), "REFERRER_POLICY")
			}
			return err == nil || !strings.Contains(err.Error(), "REFERRER_POLICY must not be empty")
		},
		gen.AnyString(),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 23: Configuration range validation
// For any numeric configuration value outside acceptable ranges, the API startup should
// fail with an error message identifying the invalid value and acceptable range.
// Validates: Requirements 7.2
func TestProperty23_ConfigurationRangeValidation(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 20

	properties := gopter.NewProperties(parameters)

	// Property: Non-positive MaxVideoIDLength should fail validation
	properties.Property("non-positive MaxVideoIDLength is rejected", prop.ForAll(
		func(length int) bool {
			cfg := validSecurityConfig()
			cfg.MaxVideoIDLength = length

			err := cfg.Validate()
			if length <= 0 {
				return err != nil && strings.Contains(err.Error(), "MAX_VIDEO_ID_LENGTH must be positive")
			}
			return err == nil || !strings.Contains(err.Error(), "MAX_VIDEO_ID_LENGTH")
		},
		gen.IntRange(-1000, 1000),
	))

	// Property: Non-positive MaxPlaylistIDLength should fail validation
	properties.Property("non-positive MaxPlaylistIDLength is rejected", prop.ForAll(
		func(length int) bool {
			cfg := validSecurityConfig()
			cfg.MaxPlaylistIDLength = length

			err := cfg.Validate()
			if length <= 0 {
				return err != nil && strings.Contains(err.Error(), "MAX_PLAYLIST_ID_LENGTH must be positive")
			}
			return err == nil || !strings.Contains(err.Error(), "MAX_PLAYLIST_ID_LENGTH")
		},
		gen.IntRange(-1000, 1000),
	))

	// Property: Non-positive MaxRequestBodySize should fail validation
	properties.Property("non-positive MaxRequestBodySize is rejected", prop.ForAll(
		func(size int64) bool {
			cfg := validSecurityConfig()
			cfg.MaxRequestBodySize = size

			err := cfg.Validate()
			if size <= 0 {
				return err != nil && strings.Contains(err.Error(), "MAX_REQUEST_BODY_SIZE must be positive")
			}
			return err == nil || !strings.Contains(err.Error(), "MAX_REQUEST_BODY_SIZE")
		},
		gen.Int64Range(-1000000, 1000000),
	))

	// Property: Non-positive MaxURLLength should fail validation
	properties.Property("non-positive MaxURLLength is rejected", prop.ForAll(
		func(length int) bool {
			cfg := validSecurityConfig()
			cfg.MaxURLLength = length

			err := cfg.Validate()
			if length <= 0 {
				return err != nil && strings.Contains(err.Error(), "MAX_URL_LENGTH must be positive")
			}
			return err == nil || !strings.Contains(err.Error(), "MAX_URL_LENGTH")
		},
		gen.IntRange(-1000, 1000),
	))

	// Property: Non-positive MaxQueryLength should fail validation
	properties.Property("non-positive MaxQueryLength is rejected", prop.ForAll(
		func(length int) bool {
			cfg := validSecurityConfig()
			cfg.MaxQueryLength = length

			err := cfg.Validate()
			if length <= 0 {
				return err != nil && strings.Contains(err.Error(), "MAX_QUERY_LENGTH must be positive")
			}
			return err == nil || !strings.Contains(err.Error(), "MAX_QUERY_LENGTH")
		},
		gen.IntRange(-1000, 1000),
	))

	// Property: Non-positive MaxHeaderSize should fail validation
	properties.Property("non-positive MaxHeaderSize is rejected", prop.ForAll(
		func(size int) bool {
			cfg := validSecurityConfig()
			cfg.MaxHeaderSize = size

			err := cfg.Validate()
			if size <= 0 {
				return err != nil && strings.Contains(err.Error(), "MAX_HEADER_SIZE must be positive")
			}
			return err == nil || !strings.Contains(err.Error(), "MAX_HEADER_SIZE")
		},
		gen.IntRange(-1000, 1000),
	))

	// Property: HSTS max-age below minimum should fail when HSTS is enabled
	properties.Property("HSTS max-age below minimum is rejected when enabled", prop.ForAll(
		func(maxAge int) bool {
			cfg := validSecurityConfig()
			cfg.EnableHSTS = true
			cfg.HSTSMaxAge = maxAge

			err := cfg.Validate()
			if maxAge < 31536000 {
				return err != nil && strings.Contains(err.Error(), "HSTS_MAX_AGE must be at least 31536000")
			}
			return err == nil || !strings.Contains(err.Error(), "HSTS_MAX_AGE")
		},
		gen.IntRange(0, 50000000),
	))

	// Property: HSTS max-age below minimum should NOT fail when HSTS is disabled
	properties.Property("HSTS max-age below minimum is allowed when disabled", prop.ForAll(
		func(maxAge int) bool {
			cfg := validSecurityConfig()
			cfg.EnableHSTS = false
			cfg.HSTSMaxAge = maxAge

			err := cfg.Validate()
			// Should not fail due to HSTS max-age when HSTS is disabled
			return err == nil || !strings.Contains(err.Error(), "HSTS_MAX_AGE")
		},
		gen.IntRange(0, 50000000),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 26: IP list format validation
// For any IP allowlist or blocklist configuration, if it contains invalid IP addresses
// or CIDR notation, the API startup should fail with an error message identifying the invalid entry.
// Validates: Requirements 7.7
func TestProperty26_IPListFormatValidation(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 20

	properties := gopter.NewProperties(parameters)

	// Generator for valid IPv4 addresses
	validIPv4Gen := gen.SliceOfN(4, gen.IntRange(0, 255)).Map(func(octets []int) string {
		return strings.Join([]string{
			itoa(octets[0]), itoa(octets[1]), itoa(octets[2]), itoa(octets[3]),
		}, ".")
	})

	// Generator for valid IPv4 CIDR ranges
	validIPv4CIDRGen := gen.SliceOfN(4, gen.IntRange(0, 255)).FlatMap(func(octets interface{}) gopter.Gen {
		o := octets.([]int)
		return gen.IntRange(0, 32).Map(func(prefix int) string {
			return strings.Join([]string{
				itoa(o[0]), itoa(o[1]), itoa(o[2]), itoa(o[3]),
			}, ".") + "/" + itoa(prefix)
		})
	}, reflect.TypeOf(""))

	// Property: Valid IPv4 addresses should pass validation
	properties.Property("valid IPv4 addresses pass validation", prop.ForAll(
		func(ip string) bool {
			cfg := validSecurityConfig()
			cfg.IPAllowlist = []string{ip}

			err := cfg.Validate()
			return err == nil
		},
		validIPv4Gen,
	))

	// Property: Valid IPv4 CIDR ranges should pass validation
	properties.Property("valid IPv4 CIDR ranges pass validation", prop.ForAll(
		func(cidr string) bool {
			cfg := validSecurityConfig()
			cfg.IPBlocklist = []string{cidr}

			err := cfg.Validate()
			return err == nil
		},
		validIPv4CIDRGen,
	))

	// Property: Invalid IP addresses should fail validation
	properties.Property("invalid IP addresses fail validation", prop.ForAll(
		func(invalidIP string) bool {
			cfg := validSecurityConfig()
			cfg.IPAllowlist = []string{invalidIP}

			err := cfg.Validate()
			return err != nil && strings.Contains(err.Error(), "invalid")
		},
		gen.OneConstOf(
			"256.1.1.1",       // Invalid octet
			"1.2.3",           // Missing octet
			"1.2.3.4.5",       // Too many octets
			"abc.def.ghi.jkl", // Non-numeric
			"192.168.1.1/33",  // Invalid CIDR prefix
			"not-an-ip",       // Random string
			"192.168.1.1/abc", // Non-numeric CIDR prefix
		),
	))

	// Property: Invalid CIDR ranges should fail validation
	properties.Property("invalid CIDR ranges fail validation", prop.ForAll(
		func(invalidCIDR string) bool {
			cfg := validSecurityConfig()
			cfg.IPBlocklist = []string{invalidCIDR}

			err := cfg.Validate()
			return err != nil && strings.Contains(err.Error(), "invalid")
		},
		gen.OneConstOf(
			"192.168.1.0/33",  // Invalid prefix for IPv4
			"10.0.0.0/-1",     // Negative prefix
			"invalid/24",     // Invalid IP part
			"192.168.1.1/",   // Missing prefix
		),
	))

	// Property: Empty IP lists should pass validation
	properties.Property("empty IP lists pass validation", prop.ForAll(
		func(_ int) bool {
			cfg := validSecurityConfig()
			cfg.IPAllowlist = []string{}
			cfg.IPBlocklist = []string{}

			err := cfg.Validate()
			return err == nil
		},
		gen.Int(),
	))

	properties.TestingRun(t)
}

// Helper function to convert int to string
func itoa(i int) string {
	return strconv.Itoa(i)
}

// validSecurityConfig returns a valid SecurityConfig for testing
func validSecurityConfig() SecurityConfig {
	return SecurityConfig{
		MaxVideoIDLength:     200,
		MaxPlaylistIDLength:  200,
		AllowedPlatforms:     []string{"youtube", "bilibili"},
		AllowedQualities:     []string{"best", "1080p", "720p"},
		MaxRequestBodySize:   1048576,
		MaxURLLength:         2048,
		MaxQueryLength:       1024,
		MaxHeaderSize:        8192,
		IPAllowlist:          []string{},
		IPBlocklist:          []string{},
		EnableIPControl:      false,
		EnableHSTS:           true,
		HSTSMaxAge:           31536000,
		CSPDirectives:        "default-src 'self'",
		ReferrerPolicy:       "strict-origin-when-cross-origin",
		PermissionsPolicy:    "geolocation=(), microphone=(), camera=()",
		EnableAuditLog:       true,
		AuditLogPath:         "logs/audit.log",
		ExposeDetailedErrors: false,
	}
}
