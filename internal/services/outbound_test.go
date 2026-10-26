package services

import (
	"net/http"
	"net/netip"
	"strings"
	"testing"
)

func TestValidateStreamURL(t *testing.T) {
	tests := []struct {
		raw string
		wantOK bool
	}{
		{"https://r1---sn.example.org/videoplayback?token=abc", true},
		{"http://cdn.example.org/media.mp4", true},
		{"https://8.8.8.8/stream", true},
		{"http://127.0.0.1:8000/admin", false},
		{"http://[::1]/metadata", false},
		{"http://169.254.169.254/latest/meta-data", false},
		{"http://100.64.0.1/stream", false},
		{"http://localhost/stream", false},
		{"http://foo.localhost/a", false},
		{"file:///etc/passwd", false},
		{"ftp://example.org/stream", false},
		{"https://user:password@example.org/stream", false},
		{"https://example.org/\r\nSet-Cookie: x", false},
		{"not a URL", false},
	}
	for _, tt := range tests {
		t.Run(tt.raw, func(t *testing.T) {
			err := validateStreamURL(tt.raw)
			if (err == nil) != tt.wantOK {
				t.Fatalf("validateStreamURL(%q) error = %v, wantOK=%v", tt.raw, err, tt.wantOK)
			}
		})
	}
}

func TestIsPublicStreamIP(t *testing.T) {
	for _, tc := range []struct {
		ip string
		want bool
	}{
		{"8.8.8.8", true},
		{"2606:4700:4700::1111", true},
		{"127.0.0.1", false},
		{"192.168.1.1", false},
		{"10.0.0.1", false},
		{"169.254.169.254", false},
		{"100.64.0.1", false},
		{"198.18.0.1", false},
		{"192.0.2.1", false},
		{"::1", false},
		{"fc00::1", false},
		{"2001:db8::1", false},
		{"::ffff:127.0.0.1", false},
	} {
		ip := netip.MustParseAddr(tc.ip)
		if got := isPublicStreamIP(ip); got != tc.want {
			t.Errorf("isPublicStreamIP(%s) = %v, want %v", tc.ip, got, tc.want)
		}
	}
}

func TestSanitizeStreamURLSkipsWarningsAndUnsafeSchemes(t *testing.T) {
	got, err := sanitizeStreamURL("WARNING: extractor message\nfile:///etc/passwd\nhttps://cdn.example.org/video.mp4\n")
	if err != nil || got != "https://cdn.example.org/video.mp4" {
		t.Fatalf("unexpected URL %q, error %v", got, err)
	}
	_, err = sanitizeStreamURL("WARNING: failure\nhttp://127.0.0.1/secret\n")
	if err == nil {
		t.Fatal("expected error for unsafe output")
	}
}

func TestCopySafeStreamHeaders(t *testing.T) {
	src := http.Header{}
	src.Set("Authorization", "Bearer secret")
	src.Set("X-Api-Key", "secret")
	src.Set("Cookie", "session=secret")
	src.Set("Range", "bytes=0-1023")
	src.Set("If-Range", "etag")
	dst := http.Header{}
	copySafeStreamRequestHeaders(dst, src)
	if got := dst.Get("Range"); got != "bytes=0-1023" {
		t.Fatalf("lost Range: %q", got)
	}
	if got := dst.Get("If-Range"); got != "etag" {
		t.Fatalf("lost If-Range: %q", got)
	}
	for _, key := range []string{"Authorization", "X-Api-Key", "Cookie"} {
		if got := dst.Get(key); got != "" {
			t.Fatalf("leaked %s: %q", key, got)
		}
	}
	resp := http.Header{}
	resp.Set("Content-Type", "video/mp4")
	resp.Set("Content-Range", "bytes 0-1023/4096")
	resp.Set("Set-Cookie", "secret=x")
	resp.Set("Connection", "keep-alive")
	back := http.Header{}
	copySafeStreamResponseHeaders(back, resp)
	if back.Get("Content-Type") != "video/mp4" || back.Get("Content-Range") == "" {
		t.Fatal("expected media headers to be preserved")
	}
	if back.Get("Set-Cookie") != "" || back.Get("Connection") != "" {
		t.Fatal("unsafe upstream headers leaked")
	}
}

func TestDialPublicStreamAddressRejectsLoopback(t *testing.T) {
	_, err := dialPublicStreamAddress(t.Context(), "tcp", "127.0.0.1:80")
	if err == nil || !strings.Contains(err.Error(), "blocked") {
		t.Fatalf("expected blocked loopback: %v", err)
	}
}

func TestFormatSelectorReturnsMuxedSingleTrack(t *testing.T) {
	var video VideoService
	for _, tc := range []struct{ quality, want string }{
		{"best", "best"},
		{"worst", "worst"},
		{"1080p", "best[ext=mp4][height<=1080]/best[height<=1080]"},
		{"720p", "best[ext=mp4][height<=720]/best[height<=720]"},
		{"480p", "best[ext=mp4][height<=480]/best[height<=480]"},
		{"360p", "best[ext=mp4][height<=360]/best[height<=360]"},
	} {
		got := video.getFormatSelector(tc.quality)
		if got != tc.want {
			t.Errorf("quality %q: got %q, want %q", tc.quality, got, tc.want)
		}
		if strings.ContainsAny(got, "+") {
			t.Errorf("format selector %q includes separate video/audio tracks", got)
		}
	}
}

func TestSanitizeStreamURLRejectsMultipleURLs(t *testing.T) {
	for _, raw := range []string{
		"https://media.example.com/video-only\nhttps://media.example.com/audio-only",
		"https://media.example.com/video-only\nWARNING: message\nhttps://media.example.com/audio-only",
	} {
		if got, err := sanitizeStreamURL(raw); err == nil {
			t.Errorf("accepted ambiguous two-URL output: %q", got)
		}
	}
	if got, err := sanitizeStreamURL("WARNING: message\nhttps://media.example.com/muxed.mp4"); err != nil || got != "https://media.example.com/muxed.mp4" {
		t.Fatalf("valid muxed URL rejected: %q (%v)", got, err)
	}
}
