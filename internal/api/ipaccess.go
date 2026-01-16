package api

import (
	"net"
	"strings"
)

// IPAccessController defines the interface for IP-based access control.
type IPAccessController interface {
	IsAllowed(ip string) bool
	IsBlocked(ip string) bool
}

// CIDRAccessController implements IP access control using CIDR ranges.
type CIDRAccessController struct {
	allowlist []*net.IPNet
	blocklist []*net.IPNet
	enabled   bool
}

// NewCIDRAccessController creates a new IP access controller.
func NewCIDRAccessController(allowlist, blocklist []string, enabled bool) (*CIDRAccessController, error) {
	allowNets, err := ParseCIDRList(allowlist)
	if err != nil {
		return nil, err
	}

	blockNets, err := ParseCIDRList(blocklist)
	if err != nil {
		return nil, err
	}

	return &CIDRAccessController{
		allowlist: allowNets,
		blocklist: blockNets,
		enabled:   enabled,
	}, nil
}

// ParseCIDRList parses a list of IP addresses or CIDR ranges into net.IPNet.
func ParseCIDRList(cidrs []string) ([]*net.IPNet, error) {
	result := make([]*net.IPNet, 0, len(cidrs))

	for _, cidr := range cidrs {
		cidr = strings.TrimSpace(cidr)
		if cidr == "" {
			continue
		}

		// If no CIDR notation, add appropriate suffix
		if !strings.Contains(cidr, "/") {
			ip := net.ParseIP(cidr)
			if ip == nil {
				continue // Skip invalid IPs
			}
			// Add /32 for IPv4 or /128 for IPv6
			if ip.To4() != nil {
				cidr = cidr + "/32"
			} else {
				cidr = cidr + "/128"
			}
		}

		_, ipNet, err := net.ParseCIDR(cidr)
		if err != nil {
			continue // Skip invalid CIDRs
		}
		result = append(result, ipNet)
	}

	return result, nil
}


// IsBlocked checks if an IP is in the blocklist.
// Requirements: 5.2, 5.5, 5.6
func (c *CIDRAccessController) IsBlocked(ipStr string) bool {
	if !c.enabled || len(c.blocklist) == 0 {
		return false
	}

	ip := net.ParseIP(strings.TrimSpace(ipStr))
	if ip == nil {
		return false // Invalid IP, let other validation handle it
	}

	for _, ipNet := range c.blocklist {
		if ipNet.Contains(ip) {
			return true
		}
	}

	return false
}

// IsAllowed checks if an IP is in the allowlist.
// If allowlist is empty, all IPs are allowed (unless blocked).
// Requirements: 5.1, 5.5, 5.6
func (c *CIDRAccessController) IsAllowed(ipStr string) bool {
	if !c.enabled {
		return true
	}

	// If no allowlist configured, allow all (blocklist still applies)
	if len(c.allowlist) == 0 {
		return true
	}

	ip := net.ParseIP(strings.TrimSpace(ipStr))
	if ip == nil {
		return false // Invalid IP
	}

	for _, ipNet := range c.allowlist {
		if ipNet.Contains(ip) {
			return true
		}
	}

	return false
}

// IsEnabled returns whether IP access control is enabled.
func (c *CIDRAccessController) IsEnabled() bool {
	return c.enabled
}

// GetClientIP extracts the real client IP from request headers.
// Checks X-Forwarded-For, X-Real-IP, CF-Connecting-IP in order.
func GetClientIP(headers map[string][]string, remoteAddr string) string {
	// Check CF-Connecting-IP (Cloudflare)
	if cfIP := getHeader(headers, "CF-Connecting-IP"); cfIP != "" {
		return cfIP
	}

	// Check X-Real-IP
	if realIP := getHeader(headers, "X-Real-IP"); realIP != "" {
		return realIP
	}

	// Check X-Forwarded-For (take first IP)
	if xff := getHeader(headers, "X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		if len(parts) > 0 {
			return strings.TrimSpace(parts[0])
		}
	}

	// Fall back to remote address
	if remoteAddr != "" {
		// Remove port if present
		host, _, err := net.SplitHostPort(remoteAddr)
		if err != nil {
			return remoteAddr
		}
		return host
	}

	return ""
}

func getHeader(headers map[string][]string, key string) string {
	if values, ok := headers[key]; ok && len(values) > 0 {
		return strings.TrimSpace(values[0])
	}
	return ""
}
