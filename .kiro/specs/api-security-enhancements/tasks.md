# Implementation Plan: API Security Enhancements

## Overview

This implementation plan breaks down the API security enhancements into discrete, incremental tasks. Each task builds on previous work and includes property-based tests to validate correctness. The implementation follows Go best practices and integrates with the existing Gin middleware architecture.

## Tasks

- [x] 1. Set up security configuration and validation
  - [x] 1.1 Extend Config struct with security configuration fields
    - Add SecurityConfig fields to `internal/config/config.go`
    - Add environment variable parsing for all security settings
    - Add default values for non-sensitive options
    - _Requirements: 7.4, 7.6_

  - [x] 1.2 Implement configuration validation
    - Create `ValidateSecurityConfig()` function
    - Validate required fields are present
    - Validate numeric values are within acceptable ranges
    - Validate IP lists are in valid CIDR format
    - Return descriptive errors for invalid configuration
    - _Requirements: 7.1, 7.2, 7.7, 7.8_

  - [x] 1.3 Write property tests for configuration validation
    - **Property 22: Required configuration validation**
    - **Property 23: Configuration range validation**
    - **Property 26: IP list format validation**
    - **Validates: Requirements 7.1, 7.2, 7.7**

- [x] 2. Implement input validation component
  - [x] 2.1 Create InputValidator interface and implementation
    - Create `internal/api/validation.go`
    - Implement `ValidatePlatform()` - check against allowed platforms list
    - Implement `ValidateVideoID()` - alphanumeric, hyphens, underscores, max 200 chars
    - Implement `ValidatePlaylistID()` - same rules as video ID
    - Implement `ValidateQuality()` - check against allowed qualities list
    - Implement `ValidateCountryCode()` - valid 2-letter ISO code regex
    - Implement `ValidateMode()` - must be "proxy" or "direct"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 2.2 Create validation middleware
    - Create `ValidationMiddleware()` in `internal/api/middleware.go`
    - Extract and validate parameters from request
    - Return 400 Bad Request with structured error response on failure
    - Pass validated parameters to handlers via context
    - _Requirements: 1.7_

  - [x] 2.3 Write property tests for input validation
    - **Property 1: Parameter validation rejects invalid inputs**
    - **Property 2: Validation failures return 400 with descriptive errors**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

- [x] 3. Implement input sanitization component
  - [x] 3.1 Create InputSanitizer interface and implementation
    - Create `internal/api/sanitization.go`
    - Implement `SanitizePath()` - remove path traversal sequences
    - Implement `SanitizeURL()` - decode and validate URL-encoded values
    - Implement `SanitizeParameter()` - general parameter sanitization
    - Implement `DetectMaliciousPatterns()` - SQL injection, XSS, command injection
    - Implement `ContainsNullOrControlChars()` - detect forbidden characters
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.2 Create sanitization middleware
    - Create `SanitizationMiddleware()` in `internal/api/middleware.go`
    - Apply sanitization to all request parameters
    - Reject requests with null bytes or control characters
    - Log malicious pattern detections
    - _Requirements: 2.4, 2.5_

  - [x] 3.3 Write property tests for input sanitization
    - **Property 4: Path traversal sequences are removed**
    - **Property 5: URL-encoded values are decoded and validated**
    - **Property 6: Null bytes and control characters are rejected**
    - **Validates: Requirements 2.1, 2.2, 2.4**

- [x] 4. Checkpoint - Validate input handling
  - Ensure all tests pass, ask the user if questions arise.
  - Verify validation and sanitization work together correctly

- [x] 5. Implement enhanced security headers
  - [x] 5.1 Update SecurityHeadersMiddleware
    - Update `SecurityHeadersMiddleware()` in `internal/api/middleware.go`
    - Add Content-Security-Policy header with configurable directives
    - Add Strict-Transport-Security header (conditional on HSTS enabled)
    - Add Referrer-Policy header
    - Add Permissions-Policy header
    - Keep existing X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
    - Make headers configurable via SecurityConfig
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 5.2 Write property tests for security headers
    - **Property 8: All required security headers are present**
    - **Property 9: HSTS max-age meets minimum requirement**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

- [x] 6. Implement request size limits
  - [x] 6.1 Create request size limit middleware
    - Create `RequestSizeLimitMiddleware()` in `internal/api/middleware.go`
    - Implement body size limit using `http.MaxBytesReader`
    - Implement URL length check
    - Implement query string length check
    - Implement header size check
    - Return 413 Payload Too Large when limits exceeded
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.2 Write property tests for size limits
    - **Property 10: Size limits are enforced**
    - **Property 11: Size limit violations return 413**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

- [x] 7. Implement IP-based access controls
  - [x] 7.1 Create IP access control component
    - Create `internal/api/ipaccess.go`
    - Implement `ParseCIDRList()` - parse IP/CIDR strings to net.IPNet
    - Implement `CIDRAccessController` struct with allowlist and blocklist
    - Implement `IsAllowed()` - check if IP is in allowlist
    - Implement `IsBlocked()` - check if IP is in blocklist
    - Support both IPv4 and IPv6 addresses
    - _Requirements: 5.5, 5.6_

  - [x] 7.2 Create IP access control middleware
    - Create `IPAccessControlMiddleware()` in `internal/api/middleware.go`
    - Extract client IP from headers (X-Forwarded-For, X-Real-IP, CF-Connecting-IP)
    - Check blocklist first (deny takes precedence)
    - Check allowlist if configured
    - Return 403 Forbidden for blocked/non-allowed IPs
    - Ensure middleware executes before all other processing
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.8_

  - [x] 7.3 Write property tests for IP access control
    - **Property 13: Allowlist enforcement**
    - **Property 14: Blocklist enforcement**
    - **Property 15: IPv4 and IPv6 support**
    - **Property 16: CIDR range matching**
    - **Property 18: IP access control executes first**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.8**

- [x] 8. Checkpoint - Validate access controls
  - Ensure all tests pass, ask the user if questions arise.
  - Verify IP access control integrates correctly with other middleware

- [x] 9. Implement audit logging
  - [x] 9.1 Create audit logger component
    - Create `internal/services/audit.go`
    - Implement `AuditLogger` interface
    - Implement `AuditLogEntry` struct with all required fields
    - Implement `LogValidationFailure()` method
    - Implement `LogAccessDenied()` method
    - Implement `LogSizeLimitExceeded()` method
    - Implement `LogSuspiciousActivity()` method
    - Implement `LogPanicRecovered()` method
    - Generate and include request ID in all entries
    - Format as JSON in production environments
    - Write to separate log stream from application logs
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [x] 9.2 Integrate audit logging with middleware
    - Add audit logger to Handler struct
    - Call audit logger from validation middleware on failures
    - Call audit logger from sanitization middleware on malicious patterns
    - Call audit logger from IP access control middleware on blocks
    - Call audit logger from size limit middleware on violations
    - Update recovery middleware to call audit logger on panics
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 9.3 Write property tests for audit logging
    - **Property 19: Audit log completeness**
    - **Property 20: Request ID correlation**
    - **Property 21: Audit log separation**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.8**

- [x] 10. Implement secure error handling
  - [x] 10.1 Create secure error response handler
    - Create `internal/api/errors.go`
    - Implement `SecureErrorResponse()` function
    - Return generic messages to clients
    - Log detailed error information internally
    - Strip file paths, stack traces, database details from responses
    - Include debug info only in development environment
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 10.2 Update existing error handling
    - Update `errorResponse()` in handlers.go to use secure error handler
    - Update recovery middleware to use secure error handler
    - Ensure all error paths use secure error handling
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 8.6_

  - [x] 10.3 Write property tests for error handling
    - **Property 27: Generic error messages to clients**
    - **Property 28: Detailed errors logged internally**
    - **Property 24: Sensitive data not logged**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 7.3**

- [x] 11. Integrate all security middleware
  - [x] 11.1 Update routes.go with security middleware stack
    - Update `SetupRoutes()` in `internal/api/routes.go`
    - Add middleware in correct order: IP Access → Size Limits → Validation → Sanitization → Security Headers
    - Pass security configuration to middleware
    - Ensure audit logger is available to all middleware
    - _Requirements: 5.8_

  - [x] 11.2 Update main.go with security initialization
    - Load and validate security configuration on startup
    - Initialize audit logger
    - Initialize IP access controller
    - Pass security components to route setup
    - Fail startup on configuration validation errors
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 11.3 Write integration tests
    - Test full request flow with all security middleware
    - Test middleware execution order
    - Test configuration loading from environment
    - Verify audit log file creation
    - _Requirements: 5.8, 7.1, 7.2_

- [x] 12. Final checkpoint - Complete validation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all security features work together
  - Review audit logs for completeness
  - Test with various attack patterns

## Notes

- All tasks are required for comprehensive security coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The `gopter` library will be used for property-based testing in Go
