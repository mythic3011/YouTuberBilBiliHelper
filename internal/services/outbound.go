package services

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"strings"
	"time"
)

// Outbound media responses can take minutes. Bound *idle* reads, not the
// total download time, so slow but active streams can finish.
const streamReadIdleTimeout = 45 * time.Second

type readIdleConn struct {
	net.Conn
	timeout time.Duration
}

func (c *readIdleConn) Read(buf []byte) (int, error) {
	if err := c.Conn.SetReadDeadline(time.Now().Add(c.timeout)); err != nil {
		return 0, err
	}
	return c.Conn.Read(buf)
}

// Reserved address ranges not all covered by netip.Addr.IsPrivate.
var blockedIPv4Ranges = []netip.Prefix{
	netip.MustParsePrefix("100.64.0.0/10"), // Shared address space (CGNAT)
	netip.MustParsePrefix("192.0.0.0/24"),
	netip.MustParsePrefix("192.0.2.0/24"),
	netip.MustParsePrefix("198.18.0.0/15"), // Benchmark networks
	netip.MustParsePrefix("198.51.100.0/24"),
	netip.MustParsePrefix("203.0.113.0/24"),
	netip.MustParsePrefix("240.0.0.0/4"),
}

var blockedIPv6Ranges = []netip.Prefix{
	netip.MustParsePrefix("2001:db8::/32"), // Documentation range
}

func isPublicStreamIP(ip netip.Addr) bool {
	ip = ip.Unmap()
	if !ip.IsValid() || !ip.IsGlobalUnicast() || ip.IsPrivate() ||
		ip.IsLoopback() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() {
		return false
	}
	blocked := blockedIPv6Ranges
	if ip.Is4() {
		blocked = blockedIPv4Ranges
	}
	for _, prefix := range blocked {
		if prefix.Contains(ip) {
			return false
		}
	}
	return true
}

// validateStreamURL performs a cheap syntactic check. The transport separately
// validates DNS results before dialing to prevent DNS-rebinding bypasses.
func validateStreamURL(raw string) error {
	if strings.ContainsAny(raw, "\r\n\t") {
		return errors.New("stream URL contains control characters")
	}
	u, err := url.Parse(raw)
	if err != nil {
		return fmt.Errorf("invalid stream URL: %w", err)
	}
	if (u.Scheme != "http" && u.Scheme != "https") || u.Opaque != "" ||
		u.Host == "" || u.User != nil {
		return errors.New("stream URL must be an absolute HTTP(S) URL without credentials")
	}
	host := u.Hostname()
	if host == "" || len(host) > 253 ||
		strings.EqualFold(host, "localhost") ||
		strings.HasSuffix(strings.ToLower(host), ".localhost") {
		return errors.New("blocked stream URL host")
	}
	// CDN downloads use HTTP(S) ports. Prevent SSRF against arbitrary public
	// services such as databases and admin consoles on custom ports.
	if port := u.Port(); port != "" && port != "80" && port != "443" {
		return errors.New("stream URL uses a disallowed port")
	}
	if ip, err := netip.ParseAddr(host); err == nil && !isPublicStreamIP(ip) {
		return errors.New("blocked non-public stream IP")
	}
	return nil
}

// dialPublicStreamAddress resolves and dials exactly the vetted address. It
// rejects *all* answers if even one DNS record points to a private network.
func dialPublicStreamAddress(ctx context.Context, network, address string) (net.Conn, error) {
	host, port, err := net.SplitHostPort(address)
	if err != nil {
		return nil, err
	}
	ips, err := net.DefaultResolver.LookupNetIP(ctx, "ip", host)
	if err != nil {
		return nil, fmt.Errorf("resolve stream host: %w", err)
	}
	if len(ips) == 0 {
		return nil, errors.New("stream host resolved to no addresses")
	}
	for _, ip := range ips {
		if !isPublicStreamIP(ip) {
			return nil, errors.New("blocked non-public stream destination")
		}
	}
	dialer := &net.Dialer{Timeout: 10 * time.Second, KeepAlive: 30 * time.Second}
	var dialErr error
	for _, ip := range ips {
		conn, err := dialer.DialContext(ctx, network, net.JoinHostPort(ip.String(), port))
		if err == nil {
			return &readIdleConn{Conn: conn, timeout: streamReadIdleTimeout}, nil
		}
		dialErr = err
	}
	return nil, fmt.Errorf("connect stream destination: %w", dialErr)
}

var safeStreamHTTPClient = &http.Client{
	Transport: &http.Transport{
		Proxy:                 nil, // Never bypass address checks via environment HTTP proxies.
		DialContext:           dialPublicStreamAddress,
		DisableCompression:    true, // Preserve upstream range and content lengths.
		ResponseHeaderTimeout: 20 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		IdleConnTimeout:       30 * time.Second,
		MaxIdleConns:          100,
	},
	CheckRedirect: func(req *http.Request, via []*http.Request) error {
		if len(via) >= 5 {
			return errors.New("too many stream redirects")
		}
		return validateStreamURL(req.URL.String())
	},
}

// Only media seek headers may be forwarded to a third-party CDN.
func copySafeStreamRequestHeaders(dst, src http.Header) {
	for _, key := range []string{"Range", "If-Range"} {
		if value := src.Get(key); value != "" {
			dst.Set(key, value)
		}
	}
	dst.Set("Accept-Encoding", "identity")
}

// Do not copy upstream Set-Cookie, WWW-Authenticate, or hop-by-hop headers.
func copySafeStreamResponseHeaders(dst, src http.Header) {
	for _, key := range []string{
		"Content-Type", "Content-Length", "Content-Range", "Accept-Ranges",
		"ETag", "Last-Modified", "Cache-Control",
	} {
		if value := src.Get(key); value != "" {
			dst.Set(key, value)
		}
	}
}
