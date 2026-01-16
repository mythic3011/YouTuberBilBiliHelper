package config

import (
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config holds application runtime configuration.
type Config struct {
	Environment       string
	Port              string
	LogLevel          string
	RedisHost         string
	RedisPort         string
	RedisPassword     string
	RedisDB           int
	VideoInfoTTL      time.Duration
	StreamURLTTL      time.Duration
	SmartProxyEnabled bool
	ProxyCountries    []string
	DefaultStreamMode string
	Security          SecurityConfig
}

// SecurityConfig holds security-related configuration settings.
type SecurityConfig struct {
	// Input Validation
	MaxVideoIDLength    int
	MaxPlaylistIDLength int
	AllowedPlatforms    []string
	AllowedQualities    []string

	// Request Size Limits
	MaxRequestBodySize int64
	MaxURLLength       int
	MaxQueryLength     int
	MaxHeaderSize      int

	// IP Access Control
	IPAllowlist     []string
	IPBlocklist     []string
	EnableIPControl bool

	// Security Headers
	EnableHSTS        bool
	HSTSMaxAge        int
	CSPDirectives     string
	ReferrerPolicy    string
	PermissionsPolicy string

	// Audit Logging
	EnableAuditLog bool
	AuditLogPath   string

	// Error Handling
	ExposeDetailedErrors bool
}

// Load reads configuration values from environment variables with sensible defaults.
func Load() *Config {
	cfg := &Config{
		Environment:       getEnvMulti([]string{"APP_ENV", "ENVIRONMENT"}, "development"),
		Port:              getEnv("PORT", "8001"),
		LogLevel:          getEnv("LOG_LEVEL", "info"),
		RedisHost:         getEnv("REDIS_HOST", "127.0.0.1"),
		RedisPort:         getEnv("REDIS_PORT", "6379"),
		RedisPassword:     os.Getenv("REDIS_PASSWORD"),
		VideoInfoTTL:      parseDuration(getEnv("VIDEO_INFO_TTL", "15m"), 15*time.Minute),
		StreamURLTTL:      parseDuration(getEnv("STREAM_URL_TTL", "5m"), 5*time.Minute),
		SmartProxyEnabled: parseBool(getEnv("SMART_PROXY_ENABLED", "true"), true),
		ProxyCountries:    parseCSV(getEnv("PROXY_COUNTRIES", "CN")),
		DefaultStreamMode: strings.ToLower(getEnv("DEFAULT_STREAM_MODE", "direct")),
		Security:          loadSecurityConfig(),
	}

	cfg.RedisDB = parseInt(getEnv("REDIS_DB", "0"), 0)
	return cfg
}

// loadSecurityConfig loads security configuration from environment variables.
func loadSecurityConfig() SecurityConfig {
	return SecurityConfig{
		// Input Validation
		MaxVideoIDLength:    parseInt(getEnv("MAX_VIDEO_ID_LENGTH", "200"), 200),
		MaxPlaylistIDLength: parseInt(getEnv("MAX_PLAYLIST_ID_LENGTH", "200"), 200),
		AllowedPlatforms:    parseCSVLower(getEnv("ALLOWED_PLATFORMS", "youtube,bilibili,twitter,instagram,twitch")),
		AllowedQualities:    parseCSVLower(getEnv("ALLOWED_QUALITIES", "best,2160p,1440p,1080p,720p,480p,360p,worst")),

		// Request Size Limits
		MaxRequestBodySize: parseInt64(getEnv("MAX_REQUEST_BODY_SIZE", "1048576"), 1048576), // 1MB
		MaxURLLength:       parseInt(getEnv("MAX_URL_LENGTH", "2048"), 2048),
		MaxQueryLength:     parseInt(getEnv("MAX_QUERY_LENGTH", "1024"), 1024),
		MaxHeaderSize:      parseInt(getEnv("MAX_HEADER_SIZE", "8192"), 8192), // 8KB

		// IP Access Control
		IPAllowlist:     parseCSV(getEnv("IP_ALLOWLIST", "")),
		IPBlocklist:     parseCSV(getEnv("IP_BLOCKLIST", "")),
		EnableIPControl: parseBool(getEnv("ENABLE_IP_CONTROL", "false"), false),

		// Security Headers
		EnableHSTS:        parseBool(getEnv("ENABLE_HSTS", "true"), true),
		HSTSMaxAge:        parseInt(getEnv("HSTS_MAX_AGE", "31536000"), 31536000),
		CSPDirectives:     getEnv("CSP_DIRECTIVES", "default-src 'self'"),
		ReferrerPolicy:    getEnv("REFERRER_POLICY", "strict-origin-when-cross-origin"),
		PermissionsPolicy: getEnv("PERMISSIONS_POLICY", "geolocation=(), microphone=(), camera=()"),

		// Audit Logging
		EnableAuditLog: parseBool(getEnv("ENABLE_AUDIT_LOG", "true"), true),
		AuditLogPath:   getEnv("AUDIT_LOG_PATH", "logs/audit.log"),

		// Error Handling
		ExposeDetailedErrors: parseBool(getEnv("EXPOSE_DETAILED_ERRORS", "false"), false),
	}
}

func getEnv(key, fallback string) string {
	if val, ok := os.LookupEnv(key); ok && val != "" {
		return val
	}
	return fallback
}

func getEnvMulti(keys []string, fallback string) string {
	for _, key := range keys {
		if val, ok := os.LookupEnv(key); ok && val != "" {
			return val
		}
	}
	return fallback
}

func parseDuration(raw string, fallback time.Duration) time.Duration {
	if d, err := time.ParseDuration(raw); err == nil {
		return d
	}
	return fallback
}

func parseInt(raw string, fallback int) int {
	if v, err := strconv.Atoi(raw); err == nil {
		return v
	}
	return fallback
}

func parseBool(raw string, fallback bool) bool {
	if raw == "" {
		return fallback
	}
	if v, err := strconv.ParseBool(raw); err == nil {
		return v
	}
	return fallback
}

func parseCSV(raw string) []string {
	if raw == "" {
		return []string{}
	}
	parts := strings.Split(raw, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		trim := strings.TrimSpace(part)
		if trim != "" {
			result = append(result, strings.ToUpper(trim))
		}
	}
	return result
}

func parseCSVLower(raw string) []string {
	if raw == "" {
		return []string{}
	}
	parts := strings.Split(raw, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		trim := strings.TrimSpace(part)
		if trim != "" {
			result = append(result, strings.ToLower(trim))
		}
	}
	return result
}

func parseInt64(raw string, fallback int64) int64 {
	if v, err := strconv.ParseInt(raw, 10, 64); err == nil {
		return v
	}
	return fallback
}

// ValidateSecurityConfig validates the security configuration and returns an error if invalid.
func (c *SecurityConfig) Validate() error {
	var errors []string

	// Validate numeric ranges
	if c.MaxVideoIDLength <= 0 {
		errors = append(errors, "MAX_VIDEO_ID_LENGTH must be positive")
	}
	if c.MaxPlaylistIDLength <= 0 {
		errors = append(errors, "MAX_PLAYLIST_ID_LENGTH must be positive")
	}
	if c.MaxRequestBodySize <= 0 {
		errors = append(errors, "MAX_REQUEST_BODY_SIZE must be positive")
	}
	if c.MaxURLLength <= 0 {
		errors = append(errors, "MAX_URL_LENGTH must be positive")
	}
	if c.MaxQueryLength <= 0 {
		errors = append(errors, "MAX_QUERY_LENGTH must be positive")
	}
	if c.MaxHeaderSize <= 0 {
		errors = append(errors, "MAX_HEADER_SIZE must be positive")
	}

	// Validate HSTS max-age (minimum 31536000 for production)
	if c.EnableHSTS && c.HSTSMaxAge < 31536000 {
		errors = append(errors, "HSTS_MAX_AGE must be at least 31536000 seconds (1 year)")
	}

	// Validate IP allowlist format
	for _, ip := range c.IPAllowlist {
		if err := validateIPOrCIDR(ip); err != nil {
			errors = append(errors, fmt.Sprintf("invalid IP_ALLOWLIST entry '%s': %v", ip, err))
		}
	}

	// Validate IP blocklist format
	for _, ip := range c.IPBlocklist {
		if err := validateIPOrCIDR(ip); err != nil {
			errors = append(errors, fmt.Sprintf("invalid IP_BLOCKLIST entry '%s': %v", ip, err))
		}
	}

	// Validate allowed platforms is not empty
	if len(c.AllowedPlatforms) == 0 {
		errors = append(errors, "ALLOWED_PLATFORMS must not be empty")
	}

	// Validate allowed qualities is not empty
	if len(c.AllowedQualities) == 0 {
		errors = append(errors, "ALLOWED_QUALITIES must not be empty")
	}

	// Validate CSP directives are not empty
	if c.CSPDirectives == "" {
		errors = append(errors, "CSP_DIRECTIVES must not be empty")
	}

	// Validate referrer policy is not empty
	if c.ReferrerPolicy == "" {
		errors = append(errors, "REFERRER_POLICY must not be empty")
	}

	if len(errors) > 0 {
		return fmt.Errorf("security configuration validation failed: %s", strings.Join(errors, "; "))
	}

	return nil
}

// validateIPOrCIDR validates that a string is a valid IP address or CIDR range.
func validateIPOrCIDR(s string) error {
	// Try parsing as CIDR first
	if strings.Contains(s, "/") {
		_, _, err := net.ParseCIDR(s)
		if err != nil {
			return fmt.Errorf("invalid CIDR notation: %v", err)
		}
		return nil
	}

	// Try parsing as IP address
	ip := net.ParseIP(s)
	if ip == nil {
		return fmt.Errorf("invalid IP address")
	}
	return nil
}
