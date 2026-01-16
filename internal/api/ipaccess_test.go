package api

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/leanovate/gopter"
	"github.com/leanovate/gopter/gen"
	"github.com/leanovate/gopter/prop"
	"github.com/sirupsen/logrus"
)

// Feature: api-security-enhancements, Property 13: Allowlist enforcement
// For any request when IP allowlist is configured and non-empty, if the client IP
// address is not in the allowlist, then the API should reject the request with HTTP 403.
// Validates: Requirements 5.1, 5.4
func TestProperty13_AllowlistEnforcement(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Property: IPs in allowlist are allowed
	properties.Property("IPs in allowlist are allowed", prop.ForAll(
		func(lastOctet int) bool {
			ip := fmt.Sprintf("192.168.1.%d", lastOctet)
			controller, _ := NewCIDRAccessController(
				[]string{"192.168.1.0/24"},
				[]string{},
				true,
			)

			return controller.IsAllowed(ip)
		},
		gen.IntRange(0, 255),
	))

	// Property: IPs not in allowlist are denied
	properties.Property("IPs not in allowlist are denied", prop.ForAll(
		func(lastOctet int) bool {
			ip := fmt.Sprintf("10.0.0.%d", lastOctet)
			controller, _ := NewCIDRAccessController(
				[]string{"192.168.1.0/24"},
				[]string{},
				true,
			)

			return !controller.IsAllowed(ip)
		},
		gen.IntRange(0, 255),
	))

	// Property: Empty allowlist allows all IPs
	properties.Property("empty allowlist allows all IPs", prop.ForAll(
		func(a, b, c, d int) bool {
			ip := fmt.Sprintf("%d.%d.%d.%d", a, b, c, d)
			controller, _ := NewCIDRAccessController(
				[]string{},
				[]string{},
				true,
			)

			return controller.IsAllowed(ip)
		},
		gen.IntRange(1, 254),
		gen.IntRange(0, 255),
		gen.IntRange(0, 255),
		gen.IntRange(1, 254),
	))

	// Property: Middleware returns 403 for non-allowed IPs
	properties.Property("middleware returns 403 for non-allowed IPs", prop.ForAll(
		func(lastOctet int) bool {
			controller, _ := NewCIDRAccessController(
				[]string{"192.168.1.0/24"},
				[]string{},
				true,
			)

			router := gin.New()
			router.Use(IPAccessControlMiddleware(controller, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			req.Header.Set("X-Forwarded-For", fmt.Sprintf("10.0.0.%d", lastOctet))
			req.RemoteAddr = fmt.Sprintf("10.0.0.%d:12345", lastOctet)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusForbidden
		},
		gen.IntRange(1, 254),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 14: Blocklist enforcement
// For any request when IP blocklist is configured, if the client IP address is in
// the blocklist, then the API should reject the request with HTTP 403.
// Validates: Requirements 5.2, 5.3
func TestProperty14_BlocklistEnforcement(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Property: IPs in blocklist are blocked
	properties.Property("IPs in blocklist are blocked", prop.ForAll(
		func(lastOctet int) bool {
			ip := fmt.Sprintf("10.0.0.%d", lastOctet)
			controller, _ := NewCIDRAccessController(
				[]string{},
				[]string{"10.0.0.0/24"},
				true,
			)

			return controller.IsBlocked(ip)
		},
		gen.IntRange(0, 255),
	))

	// Property: IPs not in blocklist are not blocked
	properties.Property("IPs not in blocklist are not blocked", prop.ForAll(
		func(lastOctet int) bool {
			ip := fmt.Sprintf("192.168.1.%d", lastOctet)
			controller, _ := NewCIDRAccessController(
				[]string{},
				[]string{"10.0.0.0/24"},
				true,
			)

			return !controller.IsBlocked(ip)
		},
		gen.IntRange(0, 255),
	))

	// Property: Blocklist takes precedence over allowlist
	properties.Property("blocklist takes precedence over allowlist", prop.ForAll(
		func(lastOctet int) bool {
			ip := fmt.Sprintf("192.168.1.%d", lastOctet)
			controller, _ := NewCIDRAccessController(
				[]string{"192.168.0.0/16"}, // Allow entire 192.168.x.x
				[]string{"192.168.1.0/24"}, // But block 192.168.1.x
				true,
			)

			// Should be blocked even though in allowlist range
			return controller.IsBlocked(ip)
		},
		gen.IntRange(0, 255),
	))

	// Property: Middleware returns 403 for blocked IPs
	properties.Property("middleware returns 403 for blocked IPs", prop.ForAll(
		func(lastOctet int) bool {
			controller, _ := NewCIDRAccessController(
				[]string{},
				[]string{"10.0.0.0/24"},
				true,
			)

			router := gin.New()
			router.Use(IPAccessControlMiddleware(controller, logger))
			router.GET("/test", func(c *gin.Context) {
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			req.Header.Set("X-Forwarded-For", fmt.Sprintf("10.0.0.%d", lastOctet))
			req.RemoteAddr = fmt.Sprintf("10.0.0.%d:12345", lastOctet)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusForbidden
		},
		gen.IntRange(1, 254),
	))

	properties.TestingRun(t)
}

// Feature: api-security-enhancements, Property 15: IPv4 and IPv6 support
// For any IP address in either IPv4 or IPv6 format, the IP access control system
// should correctly parse and match it against configured allowlists and blocklists.
// Validates: Requirements 5.5
func TestProperty15_IPv4AndIPv6Support(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	// Property: IPv4 addresses are correctly matched
	properties.Property("IPv4 addresses are correctly matched", prop.ForAll(
		func(a, b int) bool {
			ip := fmt.Sprintf("192.168.%d.%d", a, b)
			controller, _ := NewCIDRAccessController(
				[]string{"192.168.0.0/16"},
				[]string{},
				true,
			)

			return controller.IsAllowed(ip)
		},
		gen.IntRange(0, 255),
		gen.IntRange(0, 255),
	))

	// Property: IPv6 addresses are correctly matched
	properties.Property("IPv6 addresses are correctly matched", prop.ForAll(
		func(suffix int) bool {
			ip := fmt.Sprintf("2001:db8::%d", suffix)
			controller, _ := NewCIDRAccessController(
				[]string{"2001:db8::/32"},
				[]string{},
				true,
			)

			return controller.IsAllowed(ip)
		},
		gen.IntRange(1, 1000),
	))

	// Property: IPv6 blocklist works
	properties.Property("IPv6 blocklist works", prop.ForAll(
		func(suffix int) bool {
			ip := fmt.Sprintf("2001:db8:bad::%d", suffix)
			controller, _ := NewCIDRAccessController(
				[]string{},
				[]string{"2001:db8:bad::/48"},
				true,
			)

			return controller.IsBlocked(ip)
		},
		gen.IntRange(1, 1000),
	))

	properties.TestingRun(t)
}


// Feature: api-security-enhancements, Property 16: CIDR range matching
// For any IP address and CIDR range, if the IP address falls within the CIDR range,
// then the access control system should correctly identify it as a match.
// Validates: Requirements 5.6
func TestProperty16_CIDRRangeMatching(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	// Property: /24 CIDR matches all 256 addresses
	properties.Property("/24 CIDR matches all 256 addresses", prop.ForAll(
		func(lastOctet int) bool {
			ip := fmt.Sprintf("10.20.30.%d", lastOctet)
			controller, _ := NewCIDRAccessController(
				[]string{"10.20.30.0/24"},
				[]string{},
				true,
			)

			return controller.IsAllowed(ip)
		},
		gen.IntRange(0, 255),
	))

	// Property: /16 CIDR matches entire subnet
	properties.Property("/16 CIDR matches entire subnet", prop.ForAll(
		func(c, d int) bool {
			ip := fmt.Sprintf("172.16.%d.%d", c, d)
			controller, _ := NewCIDRAccessController(
				[]string{"172.16.0.0/16"},
				[]string{},
				true,
			)

			return controller.IsAllowed(ip)
		},
		gen.IntRange(0, 255),
		gen.IntRange(0, 255),
	))

	// Property: /32 CIDR matches only single IP
	properties.Property("/32 CIDR matches only single IP", prop.ForAll(
		func(lastOctet int) bool {
			controller, _ := NewCIDRAccessController(
				[]string{"192.168.1.100/32"},
				[]string{},
				true,
			)

			exactIP := "192.168.1.100"
			otherIP := fmt.Sprintf("192.168.1.%d", lastOctet)

			exactAllowed := controller.IsAllowed(exactIP)
			otherAllowed := controller.IsAllowed(otherIP)

			if lastOctet == 100 {
				return exactAllowed && otherAllowed
			}
			return exactAllowed && !otherAllowed
		},
		gen.IntRange(0, 255),
	))

	// Property: Multiple CIDR ranges work together
	properties.Property("multiple CIDR ranges work together", prop.ForAll(
		func(choice int) bool {
			controller, _ := NewCIDRAccessController(
				[]string{"10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"},
				[]string{},
				true,
			)

			var ip string
			switch choice % 3 {
			case 0:
				ip = "10.1.2.3"
			case 1:
				ip = "172.20.1.1"
			case 2:
				ip = "192.168.100.50"
			}

			return controller.IsAllowed(ip)
		},
		gen.IntRange(0, 100),
	))

	properties.TestingRun(t)
}

// Feature: api-security-enhancements, Property 18: IP access control executes first
// For any request blocked by IP access control, no other middleware or handler logic
// should execute.
// Validates: Requirements 5.8
func TestProperty18_IPAccessControlExecutesFirst(t *testing.T) {
	parameters := gopter.DefaultTestParameters()
	parameters.MinSuccessfulTests = 100

	properties := gopter.NewProperties(parameters)

	gin.SetMode(gin.TestMode)
	logger := logrus.New()
	logger.SetLevel(logrus.ErrorLevel)

	// Property: Blocked requests don't reach handler
	properties.Property("blocked requests don't reach handler", prop.ForAll(
		func(lastOctet int) bool {
			handlerCalled := false

			controller, _ := NewCIDRAccessController(
				[]string{},
				[]string{"10.0.0.0/8"},
				true,
			)

			router := gin.New()
			router.Use(IPAccessControlMiddleware(controller, logger))
			router.GET("/test", func(c *gin.Context) {
				handlerCalled = true
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			req.Header.Set("X-Forwarded-For", fmt.Sprintf("10.0.0.%d", lastOctet))
			req.RemoteAddr = fmt.Sprintf("10.0.0.%d:12345", lastOctet)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusForbidden && !handlerCalled
		},
		gen.IntRange(1, 254),
	))

	// Property: Allowed requests reach handler
	properties.Property("allowed requests reach handler", prop.ForAll(
		func(lastOctet int) bool {
			handlerCalled := false

			controller, _ := NewCIDRAccessController(
				[]string{"192.168.0.0/16"},
				[]string{},
				true,
			)

			router := gin.New()
			router.Use(IPAccessControlMiddleware(controller, logger))
			router.GET("/test", func(c *gin.Context) {
				handlerCalled = true
				c.JSON(200, gin.H{"success": true})
			})

			req := httptest.NewRequest("GET", "/test", nil)
			req.Header.Set("X-Forwarded-For", fmt.Sprintf("192.168.1.%d", lastOctet))
			req.RemoteAddr = fmt.Sprintf("192.168.1.%d:12345", lastOctet)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			return w.Code == http.StatusOK && handlerCalled
		},
		gen.IntRange(1, 254),
	))

	properties.TestingRun(t)
}
