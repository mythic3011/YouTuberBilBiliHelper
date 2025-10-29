package services

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/sirupsen/logrus"
	"video-streaming-api/internal/config"
)

// RedisService handles Redis operations
type RedisService struct {
	client *redis.Client
	cfg    *config.Config
	logger *logrus.Logger
}

// NewRedisService creates a new Redis service
func NewRedisService(cfg *config.Config, logger *logrus.Logger) *RedisService {
	client := redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%s", cfg.RedisHost, cfg.RedisPort),
		Password: cfg.RedisPassword,
		DB:       cfg.RedisDB,
	})

	return &RedisService{
		client: client,
		cfg:    cfg,
		logger: logger,
	}
}

// Ping checks Redis connection
func (s *RedisService) Ping(ctx context.Context) error {
	return s.client.Ping(ctx).Err()
}

// Get retrieves a value from Redis
func (s *RedisService) Get(ctx context.Context, key string) (string, error) {
	val, err := s.client.Get(ctx, key).Result()
	if err == redis.Nil {
		return "", fmt.Errorf("key not found: %s", key)
	}
	return val, err
}

// Set stores a value in Redis with TTL
func (s *RedisService) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	return s.client.Set(ctx, key, value, ttl).Err()
}

// SetJSON stores a JSON-encoded value in Redis
func (s *RedisService) SetJSON(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal JSON: %w", err)
	}
	return s.Set(ctx, key, data, ttl)
}

// GetJSON retrieves and decodes a JSON value from Redis
func (s *RedisService) GetJSON(ctx context.Context, key string, dest interface{}) error {
	val, err := s.Get(ctx, key)
	if err != nil {
		return err
	}

	if err := json.Unmarshal([]byte(val), dest); err != nil {
		return fmt.Errorf("failed to unmarshal JSON: %w", err)
	}
	return nil
}

// Delete removes a key from Redis
func (s *RedisService) Delete(ctx context.Context, keys ...string) error {
	return s.client.Del(ctx, keys...).Err()
}

// Exists checks if a key exists in Redis
func (s *RedisService) Exists(ctx context.Context, key string) (bool, error) {
	count, err := s.client.Exists(ctx, key).Result()
	return count > 0, err
}

// Increment increments a counter in Redis
func (s *RedisService) Increment(ctx context.Context, key string) (int64, error) {
	return s.client.Incr(ctx, key).Result()
}

// IncrementWithExpire increments a counter and sets expiration
func (s *RedisService) IncrementWithExpire(ctx context.Context, key string, ttl time.Duration) (int64, error) {
	pipe := s.client.Pipeline()
	incrCmd := pipe.Incr(ctx, key)
	pipe.Expire(ctx, key, ttl)
	
	if _, err := pipe.Exec(ctx); err != nil {
		return 0, err
	}
	
	return incrCmd.Val(), nil
}

// GetTTL returns the remaining TTL of a key
func (s *RedisService) GetTTL(ctx context.Context, key string) (time.Duration, error) {
	return s.client.TTL(ctx, key).Result()
}

// FlushDB flushes the current database (use with caution)
func (s *RedisService) FlushDB(ctx context.Context) error {
	return s.client.FlushDB(ctx).Err()
}

// Close closes the Redis connection
func (s *RedisService) Close() error {
	return s.client.Close()
}

// GenerateCacheKey generates a cache key from components
func GenerateCacheKey(prefix string, parts ...string) string {
	key := prefix
	for _, part := range parts {
		key += ":" + part
	}
	return key
}

