package services

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/leanovate/gopter"
	"github.com/leanovate/gopter/gen"
	"github.com/leanovate/gopter/prop"
	"github.com/sirupsen/logrus"
)

// Feature: api-security-enhancements, Property 19: Audit log completeness
// For any security event, an audit log entry should be created containing at minimum:
// timestamp, request ID, event type, client IP, and event-specific details.
// Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
func TestProperty19_AuditLogCompleteness(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	// Property: Validation failure logs contain all required fields
	properties.Property("validation failure logs contain all required fields", prop.ForAll(
		func(fieldLen, valueLen, reasonLen int) bool {
			// Generate strings from lengths to avoid filtering
			field := strings.Repeat("a", fieldLen)
			value := strings.Repeat("b", valueLen)
			reason := strings.Repeat("c", reasonLen)

			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			requestID := auditLogger.GenerateRequestID()
			auditLogger.LogValidationFailure(requestID, "192.168.1.1", "GET", "/test", "TestAgent", field, value, reason)

			// Read and verify log entry
			data, err := os.ReadFile(logPath)
			if err != nil {
				return false
			}

			var entry AuditLogEntry
			if err := json.Unmarshal(data[:len(data)-1], &entry); err != nil { // Remove trailing newline
				return false
			}

			return entry.RequestID == requestID &&
				entry.EventType == EventValidationFailure &&
				entry.ClientIP == "192.168.1.1" &&
				!entry.Timestamp.IsZero() &&
				entry.Details["field"] == field
		},
		gen.IntRange(1, 49),
		gen.IntRange(0, 49),
		gen.IntRange(1, 49),
	))

	// Property: Access denied logs contain all required fields
	properties.Property("access denied logs contain all required fields", prop.ForAll(
		func(reasonLen int) bool {
			reason := strings.Repeat("r", reasonLen)

			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			requestID := auditLogger.GenerateRequestID()
			auditLogger.LogAccessDenied(requestID, "10.0.0.1", "GET", "/api/test", "TestAgent", reason)

			data, err := os.ReadFile(logPath)
			if err != nil {
				return false
			}

			var entry AuditLogEntry
			if err := json.Unmarshal(data[:len(data)-1], &entry); err != nil {
				return false
			}

			return entry.RequestID == requestID &&
				entry.EventType == EventAccessDenied &&
				entry.ClientIP == "10.0.0.1" &&
				!entry.Timestamp.IsZero()
		},
		gen.IntRange(1, 49),
	))

	// Property: Size limit exceeded logs contain all required fields
	properties.Property("size limit exceeded logs contain all required fields", prop.ForAll(
		func(limitType string, size int64) bool {
			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			requestID := auditLogger.GenerateRequestID()
			auditLogger.LogSizeLimitExceeded(requestID, "172.16.0.1", "POST", "/upload", "TestAgent", limitType, size)

			data, err := os.ReadFile(logPath)
			if err != nil {
				return false
			}

			var entry AuditLogEntry
			if err := json.Unmarshal(data[:len(data)-1], &entry); err != nil {
				return false
			}

			return entry.RequestID == requestID &&
				entry.EventType == EventSizeLimitExceeded &&
				!entry.Timestamp.IsZero() &&
				entry.Details["limit_type"] == limitType
		},
		gen.OneConstOf("url", "query", "header", "body"),
		gen.Int64Range(1000, 10000000),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 20: Request ID correlation
// For any audit log entry, it should contain a request ID that can be used for correlation.
// Validates: Requirements 6.6
func TestProperty20_RequestIDCorrelation(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	// Property: Generated request IDs are unique
	properties.Property("generated request IDs are unique", prop.ForAll(
		func(count int) bool {
			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			ids := make(map[string]bool)
			for i := 0; i < count; i++ {
				id := auditLogger.GenerateRequestID()
				if ids[id] {
					return false // Duplicate found
				}
				ids[id] = true
			}
			return true
		},
		gen.IntRange(10, 100),
	))

	// Property: Request ID is included in all log entries
	properties.Property("request ID is included in all log entries", prop.ForAll(
		func(_ int) bool {
			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			requestID := auditLogger.GenerateRequestID()

			// Log different event types
			auditLogger.LogValidationFailure(requestID, "1.1.1.1", "GET", "/", "UA", "f", "v", "r")
			auditLogger.LogAccessDenied(requestID, "1.1.1.1", "GET", "/", "UA", "blocked")
			auditLogger.LogSizeLimitExceeded(requestID, "1.1.1.1", "GET", "/", "UA", "url", 5000)

			data, err := os.ReadFile(logPath)
			if err != nil {
				return false
			}

			lines := strings.Split(strings.TrimSpace(string(data)), "\n")
			for _, line := range lines {
				var entry AuditLogEntry
				if err := json.Unmarshal([]byte(line), &entry); err != nil {
					return false
				}
				if entry.RequestID != requestID {
					return false
				}
			}
			return len(lines) == 3
		},
		gen.Int(),
	))

	// Property: Request ID format is valid UUID
	properties.Property("request ID format is valid UUID", prop.ForAll(
		func(_ int) bool {
			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			requestID := auditLogger.GenerateRequestID()

			// UUID format: 8-4-4-4-12 hex characters
			parts := strings.Split(requestID, "-")
			if len(parts) != 5 {
				return false
			}
			expectedLengths := []int{8, 4, 4, 4, 12}
			for i, part := range parts {
				if len(part) != expectedLengths[i] {
					return false
				}
			}
			return true
		},
		gen.Int(),
	))

	properties.TestingRun(t)
}

// Feature: api-security-enhancements, Property 21: Audit log separation
// For any audit log entry, it should be written to the audit log stream and not
// appear in the application log stream.
// Validates: Requirements 6.8
func TestProperty21_AuditLogSeparation(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	// Property: Audit logs are written to separate file
	properties.Property("audit logs are written to separate file", prop.ForAll(
		func(eventCount int) bool {
			tmpDir := t.TempDir()
			auditLogPath := filepath.Join(tmpDir, "audit.log")
			appLogPath := filepath.Join(tmpDir, "app.log")

			// Create app logger writing to file
			appLogFile, err := os.Create(appLogPath)
			if err != nil {
				return false
			}
			defer appLogFile.Close()

			appLogger := logrus.New()
			appLogger.SetOutput(appLogFile)
			appLogger.SetLevel(logrus.InfoLevel)

			// Create audit logger
			auditLogger, err := NewFileAuditLogger(auditLogPath, appLogger, true)
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			// Write some audit events
			for i := 0; i < eventCount; i++ {
				requestID := auditLogger.GenerateRequestID()
				auditLogger.LogValidationFailure(requestID, "1.1.1.1", "GET", "/test", "UA", "field", "value", "reason")
			}

			// Verify audit log has entries
			auditData, err := os.ReadFile(auditLogPath)
			if err != nil {
				return false
			}
			auditLines := strings.Split(strings.TrimSpace(string(auditData)), "\n")
			if len(auditLines) != eventCount {
				return false
			}

			// Verify app log does NOT have audit entries (it might be empty or have other logs)
			appData, _ := os.ReadFile(appLogPath)
			appContent := string(appData)

			// App log should not contain audit event types
			return !strings.Contains(appContent, "validation_failure") &&
				!strings.Contains(appContent, "access_denied")
		},
		gen.IntRange(1, 10),
	))

	// Property: Disabled audit logger writes nothing
	properties.Property("disabled audit logger writes nothing", prop.ForAll(
		func(_ int) bool {
			tmpDir := t.TempDir()
			logPath := filepath.Join(tmpDir, "audit.log")

			logger := logrus.New()
			logger.SetLevel(logrus.ErrorLevel)

			auditLogger, err := NewFileAuditLogger(logPath, logger, false) // Disabled
			if err != nil {
				return false
			}
			defer auditLogger.Close()

			requestID := auditLogger.GenerateRequestID()
			auditLogger.LogValidationFailure(requestID, "1.1.1.1", "GET", "/", "UA", "f", "v", "r")

			// File should not exist or be empty
			_, err = os.Stat(logPath)
			return os.IsNotExist(err)
		},
		gen.Int(),
	))

	properties.TestingRun(t)
}
