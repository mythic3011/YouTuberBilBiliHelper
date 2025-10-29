package config

import (
	"os"
	"strconv"
	"time"
)

// Config holds all application configuration
type Config struct {
	// Server configuration
	Port        string
	Environment string
	LogLevel    string

	// Redis configuration
	RedisHost     string
	RedisPort     string
	RedisPassword string
	RedisDB       int

	// Cache configuration
	CacheTTL         time.Duration
	VideoInfoTTL     time.Duration
	StreamURLTTL     time.Duration
	AuthStatusTTL    time.Duration

	// Rate limiting
	RateLimitEnabled    bool
	RateLimitMaxReq     int
	RateLimitWindowSec  int

	// Storage
	MaxStorageGB           int
	TempFileRetentionHours int
	DownloadDir            string

	// CORS
	CORSOrigins []string
}

// Load loads configuration from environment variables
func Load() *Config {
	return &Config{
		// Server
		Port:        getEnv("PORT", "8001"),
		Environment: getEnv("ENVIRONMENT", "development"),
		LogLevel:    getEnv("LOG_LEVEL", "info"),

		// Redis
		RedisHost:     getEnv("REDIS_HOST", "localhost"),
		RedisPort:     getEnv("REDIS_PORT", "6379"),
		RedisPassword: getEnv("REDIS_PASSWORD", ""),
		RedisDB:       getEnvInt("REDIS_DB", 0),

		// Cache TTLs
		CacheTTL:      time.Duration(getEnvInt("CACHE_TTL", 300)) * time.Second,
		VideoInfoTTL:  time.Duration(getEnvInt("VIDEO_INFO_TTL", 3600)) * time.Second,
		StreamURLTTL:  time.Duration(getEnvInt("STREAM_URL_TTL", 600)) * time.Second,
		AuthStatusTTL: time.Duration(getEnvInt("AUTH_STATUS_TTL", 1800)) * time.Second,

		// Rate limiting
		RateLimitEnabled:   getEnvBool("RATE_LIMIT_ENABLED", true),
		RateLimitMaxReq:    getEnvInt("RATE_LIMIT_MAX_REQUESTS", 1000),
		RateLimitWindowSec: getEnvInt("RATE_LIMIT_WINDOW", 60),

		// Storage
		MaxStorageGB:           getEnvInt("MAX_STORAGE_GB", 50),
		TempFileRetentionHours: getEnvInt("TEMP_FILE_RETENTION_HOURS", 24),
		DownloadDir:            getEnv("DOWNLOAD_DIR", "./downloads"),

		// CORS
		CORSOrigins: []string{"*"},
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolVal, err := strconv.ParseBool(value); err == nil {
			return boolVal
		}
	}
	return defaultValue
}

