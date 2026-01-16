package api

import (
	"net/url"
	"regexp"
	"strings"
)

// InputSanitizer defines the interface for sanitizing user inputs.
type InputSanitizer interface {
	SanitizePath(path string) (string, error)
	SanitizeURL(rawURL string) (string, error)
	SanitizeParameter(param string) (string, error)
	DetectMaliciousPatterns(input string) (bool, string)
	ContainsNullOrControlChars(input string) bool
}

// DefaultInputSanitizer implements InputSanitizer with security-focused rules.
type DefaultInputSanitizer struct {
	pathTraversalPatterns  []*regexp.Regexp
	sqlInjectionPatterns   []*regexp.Regexp
	xssPatterns            []*regexp.Regexp
	commandInjectionPatterns []*regexp.Regexp
}

// NewDefaultInputSanitizer creates a new sanitizer with compiled patterns.
func NewDefaultInputSanitizer() *DefaultInputSanitizer {
	return &DefaultInputSanitizer{
		pathTraversalPatterns: compilePatterns([]string{
			`\.\.\/`,           // ../
			`\.\.\\`,           // ..\
			`\.\.%2[fF]`,       // ..%2f or ..%2F (URL encoded /)
			`\.\.%5[cC]`,       // ..%5c or ..%5C (URL encoded \)
			`%2[eE]%2[eE]\/`,   // %2e%2e/ (double URL encoded ..)
			`%2[eE]%2[eE]\\`,   // %2e%2e\ (double URL encoded ..)
		}),
		sqlInjectionPatterns: compilePatterns([]string{
			`(?i)'\s*;\s*drop\s+`,
			`(?i)'\s*;\s*delete\s+`,
			`(?i)'\s*;\s*update\s+`,
			`(?i)'\s*;\s*insert\s+`,
			`(?i)union\s+select`,
			`(?i)union\s+all\s+select`,
			`(?i)'\s*or\s+'?\d*'?\s*=\s*'?\d*`,
			`(?i)'\s*or\s+1\s*=\s*1`,
			`(?i)--\s*$`,
			`(?i)/\*.*\*/`,
		}),
		xssPatterns: compilePatterns([]string{
			`(?i)<script[^>]*>`,
			`(?i)</script>`,
			`(?i)javascript\s*:`,
			`(?i)on\w+\s*=`,
			`(?i)<iframe[^>]*>`,
			`(?i)<object[^>]*>`,
			`(?i)<embed[^>]*>`,
			`(?i)<svg[^>]*onload`,
			`(?i)expression\s*\(`,
			`(?i)vbscript\s*:`,
		}),
		commandInjectionPatterns: compilePatterns([]string{
			`;\s*\w+`,           // ; command
			`\|\s*\w+`,          // | command
			`\$\([^)]+\)`,       // $(command)
			"\\x60[^`]+\\x60",   // `command`
			`&&\s*\w+`,          // && command
			`\|\|\s*\w+`,        // || command
			`>\s*\/`,            // > /path (redirect)
			`<\s*\/`,            // < /path (input redirect)
		}),
	}
}

func compilePatterns(patterns []string) []*regexp.Regexp {
	compiled := make([]*regexp.Regexp, 0, len(patterns))
	for _, p := range patterns {
		if re, err := regexp.Compile(p); err == nil {
			compiled = append(compiled, re)
		}
	}
	return compiled
}


// SanitizePath removes path traversal sequences from the input.
// Requirements: 2.1
func (s *DefaultInputSanitizer) SanitizePath(path string) (string, error) {
	if s.ContainsNullOrControlChars(path) {
		return "", &SanitizationError{
			Field:   "path",
			Message: "path contains null bytes or control characters",
			Code:    "NULL_OR_CONTROL_CHARS",
		}
	}

	// First, URL decode the path to catch encoded traversal attempts
	decoded, err := url.QueryUnescape(path)
	if err != nil {
		decoded = path // Use original if decoding fails
	}

	// Remove path traversal sequences
	sanitized := decoded
	for _, pattern := range s.pathTraversalPatterns {
		sanitized = pattern.ReplaceAllString(sanitized, "")
	}

	// Also handle literal traversal sequences
	sanitized = strings.ReplaceAll(sanitized, "../", "")
	sanitized = strings.ReplaceAll(sanitized, "..\\", "")

	// Clean up any double slashes that might result
	for strings.Contains(sanitized, "//") {
		sanitized = strings.ReplaceAll(sanitized, "//", "/")
	}

	return sanitized, nil
}

// SanitizeURL decodes and validates URL-encoded values.
// Requirements: 2.2
func (s *DefaultInputSanitizer) SanitizeURL(rawURL string) (string, error) {
	if s.ContainsNullOrControlChars(rawURL) {
		return "", &SanitizationError{
			Field:   "url",
			Message: "URL contains null bytes or control characters",
			Code:    "NULL_OR_CONTROL_CHARS",
		}
	}

	// Decode URL-encoded values
	decoded, err := url.QueryUnescape(rawURL)
	if err != nil {
		return "", &SanitizationError{
			Field:   "url",
			Message: "invalid URL encoding",
			Code:    "INVALID_ENCODING",
		}
	}

	// Check decoded value for null/control chars
	if s.ContainsNullOrControlChars(decoded) {
		return "", &SanitizationError{
			Field:   "url",
			Message: "decoded URL contains null bytes or control characters",
			Code:    "NULL_OR_CONTROL_CHARS",
		}
	}

	return decoded, nil
}

// SanitizeParameter performs general parameter sanitization.
// Requirements: 2.3
func (s *DefaultInputSanitizer) SanitizeParameter(param string) (string, error) {
	if s.ContainsNullOrControlChars(param) {
		return "", &SanitizationError{
			Field:   "parameter",
			Message: "parameter contains null bytes or control characters",
			Code:    "NULL_OR_CONTROL_CHARS",
		}
	}

	// URL decode the parameter
	decoded, err := url.QueryUnescape(param)
	if err != nil {
		decoded = param // Use original if decoding fails
	}

	// Check decoded value
	if s.ContainsNullOrControlChars(decoded) {
		return "", &SanitizationError{
			Field:   "parameter",
			Message: "decoded parameter contains null bytes or control characters",
			Code:    "NULL_OR_CONTROL_CHARS",
		}
	}

	// Trim whitespace
	sanitized := strings.TrimSpace(decoded)

	return sanitized, nil
}

// DetectMaliciousPatterns checks for SQL injection, XSS, and command injection patterns.
// Requirements: 2.4
func (s *DefaultInputSanitizer) DetectMaliciousPatterns(input string) (bool, string) {
	// Check for SQL injection
	for _, pattern := range s.sqlInjectionPatterns {
		if pattern.MatchString(input) {
			return true, "sql_injection"
		}
	}

	// Check for XSS
	for _, pattern := range s.xssPatterns {
		if pattern.MatchString(input) {
			return true, "xss"
		}
	}

	// Check for command injection
	for _, pattern := range s.commandInjectionPatterns {
		if pattern.MatchString(input) {
			return true, "command_injection"
		}
	}

	return false, ""
}

// ContainsNullOrControlChars checks for null bytes and control characters.
// Requirements: 2.4
func (s *DefaultInputSanitizer) ContainsNullOrControlChars(input string) bool {
	for _, r := range input {
		// Check for null byte
		if r == 0 {
			return true
		}
		// Check for control characters (0x01-0x1F) except tab (0x09), newline (0x0A), carriage return (0x0D)
		if r >= 0x01 && r <= 0x1F && r != 0x09 && r != 0x0A && r != 0x0D {
			return true
		}
	}
	return false
}

// SanitizationError represents a sanitization failure.
type SanitizationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
	Code    string `json:"code"`
}

func (e *SanitizationError) Error() string {
	return e.Field + ": " + e.Message
}
