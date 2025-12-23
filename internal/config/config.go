package config

import (
	"os"
	"strconv"
	"time"
)

// Config holds application runtime configuration.
type Config struct {
	Environment   string
	Port          string
	LogLevel      string
	RedisHost     string
	RedisPort     string
	RedisPassword string
	RedisDB       int
	VideoInfoTTL  time.Duration
	StreamURLTTL  time.Duration
}

// Load reads configuration values from environment variables with sensible defaults.
func Load() *Config {
	cfg := &Config{
		Environment:   getEnv("APP_ENV", "development"),
		Port:          getEnv("PORT", "8001"),
		LogLevel:      getEnv("LOG_LEVEL", "info"),
		RedisHost:     getEnv("REDIS_HOST", "127.0.0.1"),
		RedisPort:     getEnv("REDIS_PORT", "6379"),
		RedisPassword: os.Getenv("REDIS_PASSWORD"),
		VideoInfoTTL:  parseDuration(getEnv("VIDEO_INFO_TTL", "15m"), 15*time.Minute),
		StreamURLTTL:  parseDuration(getEnv("STREAM_URL_TTL", "5m"), 5*time.Minute),
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
