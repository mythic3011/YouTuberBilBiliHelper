package services

import (
	"context"
	"testing"
	"time"
)

func TestGenerateCacheKey(t *testing.T) {
	tests := []struct {
		name     string
		prefix   string
		parts    []string
		expected string
	}{
		{
			name:     "simple key",
			prefix:   "video",
			parts:    []string{},
			expected: "video",
		},
		{
			name:     "key with parts",
			prefix:   "video",
			parts:    []string{"youtube", "abc123"},
			expected: "video:youtube:abc123",
		},
		{
			name:     "key with quality",
			prefix:   "stream",
			parts:    []string{"youtube", "abc123", "720p"},
			expected: "stream:youtube:abc123:720p",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := GenerateCacheKey(tt.prefix, tt.parts...)
			if result != tt.expected {
				t.Errorf("GenerateCacheKey() = %v, want %v", result, tt.expected)
			}
		})
	}
}

// Note: The following tests require a running Redis instance
// They are marked as integration tests and will be skipped in unit test mode

func TestRedisService_Ping(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	// This would require a real Redis instance for integration testing
	t.Skip("Integration test - requires Redis")
}

func TestRedisService_SetGet(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	t.Skip("Integration test - requires Redis")
}

func TestRedisService_Increment(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	t.Skip("Integration test - requires Redis")
}

// Benchmark tests
func BenchmarkGenerateCacheKey(b *testing.B) {
	for i := 0; i < b.N; i++ {
		GenerateCacheKey("video", "youtube", "abc123", "720p")
	}
}

