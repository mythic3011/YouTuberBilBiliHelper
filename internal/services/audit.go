package services

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
)

// AuditEventType represents the type of audit event.
type AuditEventType string

const (
	EventValidationFailure  AuditEventType = "validation_failure"
	EventAccessDenied       AuditEventType = "access_denied"
	EventSizeLimitExceeded  AuditEventType = "size_limit_exceeded"
	EventSuspiciousActivity AuditEventType = "suspicious_activity"
	EventPanicRecovered     AuditEventType = "panic_recovered"
	EventSanitizationTriggered AuditEventType = "sanitization_triggered"
)

// AuditSeverity represents the severity level of an audit event.
type AuditSeverity string

const (
	SeverityInfo     AuditSeverity = "info"
	SeverityWarning  AuditSeverity = "warning"
	SeverityError    AuditSeverity = "error"
	SeverityCritical AuditSeverity = "critical"
)

// AuditLogEntry represents a structured audit log entry.
type AuditLogEntry struct {
	Timestamp time.Time              `json:"timestamp"`
	RequestID string                 `json:"request_id"`
	EventType AuditEventType         `json:"event_type"`
	ClientIP  string                 `json:"client_ip"`
	Method    string                 `json:"method"`
	Path      string                 `json:"path"`
	UserAgent string                 `json:"user_agent"`
	Details   map[string]interface{} `json:"details"`
	Severity  AuditSeverity          `json:"severity"`
}

// AuditLogger defines the interface for audit logging.
type AuditLogger interface {
	LogValidationFailure(requestID, clientIP, method, path, userAgent, field, value, reason string)
	LogAccessDenied(requestID, clientIP, method, path, userAgent, reason string)
	LogSizeLimitExceeded(requestID, clientIP, method, path, userAgent, limitType string, size int64)
	LogSuspiciousActivity(requestID, clientIP, method, path, userAgent, pattern, details string)
	LogPanicRecovered(requestID, clientIP, method, path, userAgent string, err interface{}, stack string)
	LogSanitizationTriggered(requestID, clientIP, method, path, userAgent, patternType string)
	GenerateRequestID() string
	Close() error
}


// FileAuditLogger implements AuditLogger writing to a file.
type FileAuditLogger struct {
	file       *os.File
	appLogger  *logrus.Logger
	mu         sync.Mutex
	enabled    bool
	jsonFormat bool
}

// NewFileAuditLogger creates a new file-based audit logger.
func NewFileAuditLogger(logPath string, appLogger *logrus.Logger, enabled bool) (*FileAuditLogger, error) {
	if !enabled {
		return &FileAuditLogger{
			appLogger: appLogger,
			enabled:   false,
		}, nil
	}

	// Ensure directory exists
	dir := filepath.Dir(logPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, err
	}

	// Open or create the audit log file
	file, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, err
	}

	return &FileAuditLogger{
		file:       file,
		appLogger:  appLogger,
		enabled:    true,
		jsonFormat: true,
	}, nil
}

// GenerateRequestID generates a unique request ID.
func (l *FileAuditLogger) GenerateRequestID() string {
	return uuid.New().String()
}

// writeEntry writes an audit log entry to the file.
func (l *FileAuditLogger) writeEntry(entry AuditLogEntry) {
	if !l.enabled || l.file == nil {
		return
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	data, err := json.Marshal(entry)
	if err != nil {
		l.appLogger.WithError(err).Error("Failed to marshal audit log entry")
		return
	}

	if _, err := l.file.Write(append(data, '\n')); err != nil {
		l.appLogger.WithError(err).Error("Failed to write audit log entry")
	}
}

// LogValidationFailure logs a validation failure event.
// Requirements: 6.1
func (l *FileAuditLogger) LogValidationFailure(requestID, clientIP, method, path, userAgent, field, value, reason string) {
	entry := AuditLogEntry{
		Timestamp: time.Now().UTC(),
		RequestID: requestID,
		EventType: EventValidationFailure,
		ClientIP:  clientIP,
		Method:    method,
		Path:      path,
		UserAgent: userAgent,
		Severity:  SeverityWarning,
		Details: map[string]interface{}{
			"field":  field,
			"value":  value,
			"reason": reason,
		},
	}
	l.writeEntry(entry)
}

// LogAccessDenied logs an IP access denied event.
// Requirements: 6.2
func (l *FileAuditLogger) LogAccessDenied(requestID, clientIP, method, path, userAgent, reason string) {
	entry := AuditLogEntry{
		Timestamp: time.Now().UTC(),
		RequestID: requestID,
		EventType: EventAccessDenied,
		ClientIP:  clientIP,
		Method:    method,
		Path:      path,
		UserAgent: userAgent,
		Severity:  SeverityWarning,
		Details: map[string]interface{}{
			"reason": reason,
		},
	}
	l.writeEntry(entry)
}

// LogSizeLimitExceeded logs a size limit exceeded event.
// Requirements: 6.3
func (l *FileAuditLogger) LogSizeLimitExceeded(requestID, clientIP, method, path, userAgent, limitType string, size int64) {
	entry := AuditLogEntry{
		Timestamp: time.Now().UTC(),
		RequestID: requestID,
		EventType: EventSizeLimitExceeded,
		ClientIP:  clientIP,
		Method:    method,
		Path:      path,
		UserAgent: userAgent,
		Severity:  SeverityWarning,
		Details: map[string]interface{}{
			"limit_type": limitType,
			"size":       size,
		},
	}
	l.writeEntry(entry)
}

// LogSuspiciousActivity logs suspicious activity detection.
// Requirements: 6.5
func (l *FileAuditLogger) LogSuspiciousActivity(requestID, clientIP, method, path, userAgent, pattern, details string) {
	entry := AuditLogEntry{
		Timestamp: time.Now().UTC(),
		RequestID: requestID,
		EventType: EventSuspiciousActivity,
		ClientIP:  clientIP,
		Method:    method,
		Path:      path,
		UserAgent: userAgent,
		Severity:  SeverityError,
		Details: map[string]interface{}{
			"pattern": pattern,
			"details": details,
		},
	}
	l.writeEntry(entry)
}

// LogPanicRecovered logs a recovered panic event.
// Requirements: 6.4
func (l *FileAuditLogger) LogPanicRecovered(requestID, clientIP, method, path, userAgent string, err interface{}, stack string) {
	entry := AuditLogEntry{
		Timestamp: time.Now().UTC(),
		RequestID: requestID,
		EventType: EventPanicRecovered,
		ClientIP:  clientIP,
		Method:    method,
		Path:      path,
		UserAgent: userAgent,
		Severity:  SeverityCritical,
		Details: map[string]interface{}{
			"error": err,
			"stack": stack,
		},
	}
	l.writeEntry(entry)
}

// LogSanitizationTriggered logs when sanitization detects malicious content.
func (l *FileAuditLogger) LogSanitizationTriggered(requestID, clientIP, method, path, userAgent, patternType string) {
	entry := AuditLogEntry{
		Timestamp: time.Now().UTC(),
		RequestID: requestID,
		EventType: EventSanitizationTriggered,
		ClientIP:  clientIP,
		Method:    method,
		Path:      path,
		UserAgent: userAgent,
		Severity:  SeverityWarning,
		Details: map[string]interface{}{
			"pattern_type": patternType,
		},
	}
	l.writeEntry(entry)
}

// Close closes the audit log file.
func (l *FileAuditLogger) Close() error {
	if l.file != nil {
		return l.file.Close()
	}
	return nil
}
