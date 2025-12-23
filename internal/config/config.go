package config

import (
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
	}

	cfg.RedisDB = parseInt(getEnv("REDIS_DB", "0"), 0)
	return cfg
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
