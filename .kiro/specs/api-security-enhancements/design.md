# Design Document: API Security Enhancements

## Overview

This design implements comprehensive security enhancements for the Go Video Streaming API, focusing on defense-in-depth principles. The enhancements add multiple layers of protection through input validation, sanitization, enhanced security headers, request size limits, IP-based access controls, audit logging, and secure configuration management.

The design follows Go best practices and integrates seamlessly with the existing Gin framework middleware architecture. All security features are configurable via environment variables and can be enabled/disabled based on deployment requirements.

## Architecture

### Security Middleware Stack

The security enhancements are implemented as a series of Gin middleware functions that execute in a specific order:

```
Request Flow:
1. IP Access Control Middleware (earliest - blocks before processing)
2. Request Size Limit Middleware
3. Input Validation Middleware
4. Input Sanitization Middleware
5. Enhanced Security Headers Middleware
6. Existing Middleware (Logger, CORS, Recovery)
7. Handler Execution
8. Audit Logging (cross-cutting concern)
```

### Middleware Ordering Rationale

- **IP Access Control**: First to reject blocked IPs immediately without processing
- **Request Size Limits**: Second to prevent resource exhaustion from large payloads
- **Input Validation**: Third to reject invalid requests early
- **Input Sanitization**: Fourth to clean validated inputs before handler processing
- **Security Headers**: Applied to all responses regardless of handler outcome

### Configuration Architecture

Security configuration extends the existing `Config` struct with new fields:

```go
type SecurityConfig struct {
    // Input Validation
    MaxVideoIDLength    int
    MaxPlaylistIDLength int
    AllowedPlatforms    []string
    AllowedQualities    []string
    
    // Request Size Limits
    MaxRequestBodySize  int64
    MaxURLLength        int
    MaxQueryLength      int
    MaxHeaderSize       int
    
    // IP Access Control
    IPAllowlist         []string
    IPBlocklist         []string
    EnableIPControl     bool
    
    // Security Headers
    EnableHSTS          bool
    HSTSMaxAge          int
    CSPDirectives       string
    
    // Audit Logging
    EnableAuditLog      bool
    AuditLogPath        string
    
    // Error Handling
    ExposeDetailedErrors bool
}
```

## Components and Interfaces

### 1. Input Validation Component

**Purpose**: Validate all user inputs against defined rules before processing.

**Interface**:
```go
type InputValidator interface {
    ValidatePlatform(platform string) error
    ValidateVideoID(videoID string) error
    ValidatePlaylistID(playlistID string) error
    ValidateQuality(quality string) error
    ValidateCountryCode(code string) error
    ValidateMode(mode string) error
}

type DefaultInputValidator struct {
    allowedPlatforms []string
    allowedQualities []string
    maxVideoIDLength int
    maxPlaylistIDLength int
}
```

**Validation Rules**:
- Platform: Must be in allowlist (youtube, bilibili, twitter, instagram, twitch)
- Video ID: Alphanumeric, hyphens, underscores, max 200 chars
- Playlist ID: Alphanumeric, hyphens, underscores, max 200 chars
- Quality: Must be in allowlist (best, 2160p, 1440p, 1080p, 720p, 480p, 360p, worst)
- Country Code: Must be valid 2-letter ISO code (regex: `^[A-Z]{2}$`)
- Mode: Must be "proxy" or "direct"

### 2. Input Sanitization Component

**Purpose**: Clean and normalize validated inputs to prevent injection attacks.

**Interface**:
```go
type InputSanitizer interface {
    SanitizePath(path string) (string, error)
    SanitizeURL(url string) (string, error)
    SanitizeParameter(param string) (string, error)
    DetectMaliciousPatterns(input string) bool
}

type DefaultInputSanitizer struct {
    pathTraversalPattern *regexp.Regexp
    nullBytePattern      *regexp.Regexp
    controlCharPattern   *regexp.Regexp
}
```

**Sanitization Rules**:
- Remove path traversal sequences: `../`, `..\`, `..%2F`, `..%5C`
- Reject null bytes: `\x00`
- Reject control characters: `\x00-\x1F` (except tab, newline, carriage return in specific contexts)
- URL decode and validate encoded values
- Reject SQL injection patterns: `'; DROP`, `UNION SELECT`, etc.
- Reject script injection patterns: `<script>`, `javascript:`, `onerror=`

### 3. Security Headers Component

**Purpose**: Add comprehensive security headers to all HTTP responses.

**Interface**:
```go
type SecurityHeadersConfig struct {
    EnableHSTS       bool
    HSTSMaxAge       int
    CSPDirectives    string
    ReferrerPolicy   string
    PermissionsPolicy string
}

func SecurityHeadersMiddleware(config SecurityHeadersConfig) gin.HandlerFunc
```

**Headers Applied**:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

### 4. Request Size Limit Component

**Purpose**: Enforce size limits on various parts of HTTP requests.

**Interface**:
```go
type RequestSizeLimits struct {
    MaxBodySize    int64
    MaxURLLength   int
    MaxQueryLength int
    MaxHeaderSize  int
}

func RequestSizeLimitMiddleware(limits RequestSizeLimits) gin.HandlerFunc
```

**Implementation**:
- Body size: Use `http.MaxBytesReader` wrapper
- URL length: Check `len(c.Request.URL.String())`
- Query length: Check `len(c.Request.URL.RawQuery)`
- Header size: Check total size of all headers

### 5. IP Access Control Component

**Purpose**: Allow or block requests based on client IP addresses.

**Interface**:
```go
type IPAccessController interface {
    IsAllowed(ip string) bool
    IsBlocked(ip string) bool
}

type CIDRAccessController struct {
    allowlist []*net.IPNet
    blocklist []*net.IPNet
    enabled   bool
}

func ParseCIDRList(cidrs []string) ([]*net.IPNet, error)
func IPAccessControlMiddleware(controller IPAccessController) gin.HandlerFunc
```

**Implementation**:
- Parse CIDR ranges during initialization
- Support both IPv4 and IPv6
- Check blocklist first (deny takes precedence)
- If allowlist exists and not empty, check if IP is in allowlist
- Extract real IP from headers: `X-Forwarded-For`, `X-Real-IP`, `CF-Connecting-IP`

### 6. Audit Logging Component

**Purpose**: Record security-relevant events in structured format.

**Interface**:
```go
type AuditLogger interface {
    LogValidationFailure(ctx *gin.Context, field string, value string, reason string)
    LogAccessDenied(ctx *gin.Context, reason string)
    LogSizeLimitExceeded(ctx *gin.Context, limitType string, size int64)
    LogSuspiciousActivity(ctx *gin.Context, pattern string, details string)
    LogPanicRecovered(ctx *gin.Context, err interface{}, stack string)
}

type AuditLogEntry struct {
    Timestamp   time.Time              `json:"timestamp"`
    RequestID   string                 `json:"request_id"`
    EventType   string                 `json:"event_type"`
    ClientIP    string                 `json:"client_ip"`
    Method      string                 `json:"method"`
    Path        string                 `json:"path"`
    UserAgent   string                 `json:"user_agent"`
    Details     map[string]interface{} `json:"details"`
    Severity    string                 `json:"severity"`
}
```

**Event Types**:
- `validation_failure`: Input validation failed
- `access_denied`: IP-based access control blocked request
- `size_limit_exceeded`: Request exceeded size limits
- `suspicious_activity`: Malicious patterns detected
- `panic_recovered`: Application panic caught and recovered
- `sanitization_triggered`: Input sanitization removed malicious content

### 7. Secure Configuration Component

**Purpose**: Validate and manage security configuration safely.

**Interface**:
```go
type ConfigValidator interface {
    Validate() error
    ValidateIPLists() error
    ValidateSecurityHeaders() error
    ValidateSizeLimits() error
}

func LoadSecurityConfig() (*SecurityConfig, error)
func (c *SecurityConfig) Validate() error
```

**Validation Rules**:
- Required fields must be present
- Numeric values must be positive and within reasonable ranges
- IP lists must be valid CIDR notation
- CSP directives must be valid syntax
- HSTS max-age must be >= 31536000 for production

## Data Models

### Validation Error Model

```go
type ValidationError struct {
    Field   string `json:"field"`
    Value   string `json:"value,omitempty"`
    Message string `json:"message"`
    Code    string `json:"code"`
}

type ValidationErrorResponse struct {
    Success    bool              `json:"success"`
    Error      string            `json:"error"`
    Validation []ValidationError `json:"validation"`
    Timestamp  time.Time         `json:"timestamp"`
}
```

### Audit Log Model

```go
type AuditLogEntry struct {
    Timestamp   time.Time              `json:"timestamp"`
    RequestID   string                 `json:"request_id"`
    EventType   string                 `json:"event_type"`
    ClientIP    string                 `json:"client_ip"`
    Method      string                 `json:"method"`
    Path        string                 `json:"path"`
    UserAgent   string                 `json:"user_agent"`
    Details     map[string]interface{} `json:"details"`
    Severity    string                 `json:"severity"` // info, warning, error, critical
}
```

### Security Configuration Model

```go
type SecurityConfig struct {
    // Input Validation
    MaxVideoIDLength    int      `env:"MAX_VIDEO_ID_LENGTH" default:"200"`
    MaxPlaylistIDLength int      `env:"MAX_PLAYLIST_ID_LENGTH" default:"200"`
    AllowedPlatforms    []string `env:"ALLOWED_PLATFORMS" default:"youtube,bilibili,twitter,instagram,twitch"`
    AllowedQualities    []string `env:"ALLOWED_QUALITIES" default:"best,2160p,1440p,1080p,720p,480p,360p,worst"`
    
    // Request Size Limits
    MaxRequestBodySize  int64 `env:"MAX_REQUEST_BODY_SIZE" default:"1048576"` // 1MB
    MaxURLLength        int   `env:"MAX_URL_LENGTH" default:"2048"`
    MaxQueryLength      int   `env:"MAX_QUERY_LENGTH" default:"1024"`
    MaxHeaderSize       int   `env:"MAX_HEADER_SIZE" default:"8192"` // 8KB
    
    // IP Access Control
    IPAllowlist         []string `env:"IP_ALLOWLIST" default:""`
    IPBlocklist         []string `env:"IP_BLOCKLIST" default:""`
    EnableIPControl     bool     `env:"ENABLE_IP_CONTROL" default:"false"`
    
    // Security Headers
    EnableHSTS          bool   `env:"ENABLE_HSTS" default:"true"`
    HSTSMaxAge          int    `env:"HSTS_MAX_AGE" default:"31536000"`
    CSPDirectives       string `env:"CSP_DIRECTIVES" default:"default-src 'self'"`
    ReferrerPolicy      string `env:"REFERRER_POLICY" default:"strict-origin-when-cross-origin"`
    PermissionsPolicy   string `env:"PERMISSIONS_POLICY" default:"geolocation=(), microphone=(), camera=()"`
    
    // Audit Logging
    EnableAuditLog      bool   `env:"ENABLE_AUDIT_LOG" default:"true"`
    AuditLogPath        string `env:"AUDIT_LOG_PATH" default:"logs/audit.log"`
    
    // Error Handling
    ExposeDetailedErrors bool `env:"EXPOSE_DETAILED_ERRORS" default:"false"`
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several opportunities to consolidate properties:

- **Input validation properties (1.1-1.6)** can be combined into a single comprehensive property about parameter validation
- **Security header properties (3.1-3.7)** can be combined into one property about all required headers being present
- **Size limit properties (4.1-4.4)** can be combined into one property about all size limits being enforced
- **IP access control properties (5.1-5.4)** can be consolidated into properties about allowlist and blocklist behavior
- **Audit logging properties (6.1-6.6)** can be combined into properties about audit log completeness
- **Error response properties (8.3-8.6)** can be combined into one property about sensitive data not being exposed

### Input Validation Properties

**Property 1: Parameter validation rejects invalid inputs**

*For any* request parameter (platform, video_id, playlist_id, quality, country, mode), if the parameter value does not match its validation rules, then the validation function should return an error.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

**Property 2: Validation failures return 400 with descriptive errors**

*For any* request with invalid parameters, the API should return HTTP 400 status code with a response body containing the field name, validation error message, and error code.

**Validates: Requirements 1.7**

**Property 3: Validation failures are logged**

*For any* validation failure, the API should create a log entry containing the timestamp, client IP, invalid field name, invalid value, and failure reason.

**Validates: Requirements 1.8**

### Input Sanitization Properties

**Property 4: Path traversal sequences are removed**

*For any* string containing path traversal patterns (`../`, `..\`, `..%2F`, `..%5C`), the sanitization function should return a string with all traversal sequences removed.

**Validates: Requirements 2.1**

**Property 5: URL-encoded values are decoded and validated**

*For any* URL-encoded parameter value, the sanitization function should decode it and then validate the decoded value against the same rules as non-encoded values.

**Validates: Requirements 2.2**

**Property 6: Null bytes and control characters are rejected**

*For any* string containing null bytes (`\x00`) or control characters (`\x01-\x1F` excluding tab, newline, carriage return), the sanitization function should reject the input and return an error.

**Validates: Requirements 2.4**

**Property 7: Malicious pattern detection triggers logging**

*For any* input containing malicious patterns (SQL injection, script injection, command injection), the sanitization function should log an audit entry with the client IP, detected pattern, and full parameter value.

**Validates: Requirements 2.5**

### Security Headers Properties

**Property 8: All required security headers are present**

*For any* HTTP response from the API, the response should contain all required security headers: Content-Security-Policy, Strict-Transport-Security (if HSTS enabled), Referrer-Policy, Permissions-Policy, X-Content-Type-Options, X-Frame-Options, and X-XSS-Protection.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

**Property 9: HSTS max-age meets minimum requirement**

*For any* HTTP response when HSTS is enabled, the Strict-Transport-Security header should have a max-age value of at least 31536000 seconds.

**Validates: Requirements 3.2**

### Request Size Limit Properties

**Property 10: Size limits are enforced**

*For any* request, if the request body size exceeds MaxRequestBodySize, or URL length exceeds MaxURLLength, or query string length exceeds MaxQueryLength, or any header size exceeds MaxHeaderSize, then the API should reject the request before processing.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

**Property 11: Size limit violations return 413**

*For any* request that exceeds any size limit, the API should return HTTP 413 status code.

**Validates: Requirements 4.5**

**Property 12: Size limit violations are logged**

*For any* request that exceeds size limits, the API should create a log entry containing the client IP, limit type that was exceeded, and the actual size.

**Validates: Requirements 4.6**

### IP Access Control Properties

**Property 13: Allowlist enforcement**

*For any* request when IP allowlist is configured and non-empty, if the client IP address is not in the allowlist (considering CIDR ranges), then the API should reject the request with HTTP 403.

**Validates: Requirements 5.1, 5.4**

**Property 14: Blocklist enforcement**

*For any* request when IP blocklist is configured, if the client IP address is in the blocklist (considering CIDR ranges), then the API should reject the request with HTTP 403.

**Validates: Requirements 5.2, 5.3**

**Property 15: IPv4 and IPv6 support**

*For any* IP address in either IPv4 or IPv6 format, the IP access control system should correctly parse and match it against configured allowlists and blocklists.

**Validates: Requirements 5.5**

**Property 16: CIDR range matching**

*For any* IP address and CIDR range, if the IP address falls within the CIDR range, then the access control system should correctly identify it as a match.

**Validates: Requirements 5.6**

**Property 17: IP access control logging**

*For any* request blocked by IP access control, the API should create an audit log entry containing the blocked IP address, the reason (allowlist/blocklist), and the requested endpoint.

**Validates: Requirements 5.7**

**Property 18: IP access control executes first**

*For any* request blocked by IP access control, no other middleware or handler logic should execute (verified by absence of logs from subsequent middleware).

**Validates: Requirements 5.8**

### Audit Logging Properties

**Property 19: Audit log completeness**

*For any* security event (validation failure, IP block, size limit violation, panic recovery, suspicious pattern), an audit log entry should be created containing at minimum: timestamp, request ID, event type, client IP, and event-specific details.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

**Property 20: Request ID correlation**

*For any* audit log entry, it should contain a request ID that matches the request ID in the corresponding application log entries.

**Validates: Requirements 6.6**

**Property 21: Audit log separation**

*For any* audit log entry, it should be written to the audit log stream and not appear in the application log stream (verified by checking both log destinations).

**Validates: Requirements 6.8**

### Configuration Validation Properties

**Property 22: Required configuration validation**

*For any* missing required configuration value, the API startup should fail with an error message identifying the missing configuration key.

**Validates: Requirements 7.1**

**Property 23: Configuration range validation**

*For any* numeric configuration value outside acceptable ranges (e.g., negative sizes, invalid port numbers), the API startup should fail with an error message identifying the invalid value and acceptable range.

**Validates: Requirements 7.2**

**Property 24: Sensitive data not logged**

*For any* log entry (application or audit), it should not contain sensitive configuration values such as passwords, tokens, or API keys.

**Validates: Requirements 7.3**

**Property 25: Configuration defaults**

*For any* non-sensitive configuration option, if not provided via environment variable, the API should use a documented default value.

**Validates: Requirements 7.6**

**Property 26: IP list format validation**

*For any* IP allowlist or blocklist configuration, if it contains invalid IP addresses or CIDR notation, the API startup should fail with an error message identifying the invalid entry.

**Validates: Requirements 7.7**

### Error Message Security Properties

**Property 27: Generic error messages to clients**

*For any* error response to clients, the error message should be generic and not contain internal implementation details, file paths, stack traces, database details, or service names.

**Validates: Requirements 8.1, 8.3, 8.4, 8.5, 8.6**

**Property 28: Detailed errors logged internally**

*For any* error that occurs, the internal logs should contain detailed error information including error type, stack trace (if applicable), and context information.

**Validates: Requirements 8.2**

## Error Handling

### Validation Errors

When input validation fails:
1. Return HTTP 400 Bad Request
2. Include structured validation error response with field-level details
3. Log validation failure to audit log
4. Do not process the request further

### Sanitization Errors

When input sanitization detects malicious content:
1. Return HTTP 400 Bad Request with generic message
2. Log detailed information about detected pattern to audit log
3. Include client IP for potential blocking
4. Do not expose detected pattern details to client

### Size Limit Errors

When request exceeds size limits:
1. Return HTTP 413 Payload Too Large
2. Log violation with client IP and size details
3. Terminate request processing immediately
4. Do not buffer entire oversized request

### IP Access Control Errors

When IP access control blocks a request:
1. Return HTTP 403 Forbidden with generic message
2. Log blocked IP and reason to audit log
3. Do not execute any handler logic
4. Do not expose allowlist/blocklist configuration

### Configuration Errors

When configuration validation fails at startup:
1. Log detailed error message with configuration key and issue
2. Exit application with non-zero status code
3. Do not start HTTP server
4. Do not expose configuration values in error messages

### Panic Recovery

When a panic occurs:
1. Recover from panic in middleware
2. Return HTTP 500 Internal Server Error with generic message
3. Log full stack trace and panic value to audit log
4. Continue serving other requests

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

Both types of tests are complementary and necessary for comprehensive coverage.

### Property-Based Testing

We will use the `gopter` library for property-based testing in Go. Each correctness property will be implemented as a property-based test with minimum 100 iterations.

**Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `Feature: api-security-enhancements, Property N: [property text]`
- Custom generators for:
  - Valid and invalid platform names
  - Valid and invalid video IDs (with various character sets)
  - Valid and invalid IP addresses (IPv4 and IPv6)
  - Valid and invalid CIDR ranges
  - Malicious input patterns (SQL injection, XSS, path traversal)
  - Various request sizes (within and exceeding limits)

**Example Property Test Structure**:
```go
// Feature: api-security-enhancements, Property 1: Parameter validation rejects invalid inputs
func TestProperty_ParameterValidationRejectsInvalid(t *testing.T) {
    parameters := gopter.DefaultTestParameters()
    parameters.MinSuccessfulTests = 100
    
    properties := gopter.NewProperties(parameters)
    
    properties.Property("invalid platforms are rejected", prop.ForAll(
        func(platform string) bool {
            validator := NewDefaultInputValidator(validPlatforms)
            err := validator.ValidatePlatform(platform)
            
            if isValidPlatform(platform) {
                return err == nil
            }
            return err != nil
        },
        gen.AnyString(),
    ))
    
    properties.TestingRun(t)
}
```

### Unit Testing

Unit tests will focus on:
- Specific validation rules (e.g., video ID max length of 200)
- Specific malicious patterns (e.g., `'; DROP TABLE`)
- Specific CIDR range calculations
- Specific security header values
- Configuration validation with known invalid values
- Error message format verification
- Audit log entry structure

### Integration Testing

Integration tests will verify:
- Middleware execution order
- End-to-end request flow with security middleware
- Audit log file creation and writing
- Configuration loading from environment variables
- IP access control with real HTTP requests

### Test Coverage Goals

- Minimum 80% code coverage for security components
- 100% coverage of validation rules
- 100% coverage of sanitization patterns
- All correctness properties implemented as property tests
- All edge cases covered by unit tests
