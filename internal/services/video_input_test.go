package services

import "testing"

func TestCanonicalMediaURL(t *testing.T) {
	tests := []struct {
		platform, input string
		playlist bool
		want string
	}{
		{"youtube", "dQw4w9WgXcQ", false, "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
		{"auto", "https://youtu.be/dQw4w9WgXcQ", false, "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
		{"auto", "https://music.youtube.com/watch?v=dQw4w9WgXcQ&si=abcd", false, "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
		{"youtube", "PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO", true, "https://www.youtube.com/playlist?list=PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO"},
		{"auto", "https://www.youtube.com/playlist?list=PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO", true, "https://www.youtube.com/playlist?list=PLGiCbGbC2CE3v3tofFoRBLjJS4XUMjgLO"},
		{"bilibili", "BV1xx411c7mD", false, "https://www.bilibili.com/video/BV1xx411c7mD"},
		{"auto", "https://www.bilibili.com/video/BV1xx411c7mD?p=2", false, "https://www.bilibili.com/video/BV1xx411c7mD"},
		{"x", "123456789012345", false, "https://twitter.com/i/status/123456789012345"},
		{"auto", "https://x.com/person/status/123456789012345", false, "https://twitter.com/i/status/123456789012345"},
		{"instagram", "ABC12345", false, "https://www.instagram.com/p/ABC12345/"},
		{"auto", "https://www.instagram.com/reel/ABC12345/", false, "https://www.instagram.com/reel/ABC12345/"},
		{"twitch", "123456789", false, "https://www.twitch.tv/videos/123456789"},
	}
	for _, tc := range tests {
		got, err := canonicalMediaURL(tc.platform, tc.input, tc.playlist)
		if err != nil || got != tc.want {
			t.Errorf("canonicalMediaURL(%q, %q, %v) = %q, %v; want %q", tc.platform, tc.input, tc.playlist, got, err, tc.want)
		}
	}
}

func TestCanonicalMediaURLRejectsUnsafeInputs(t *testing.T) {
	for _, raw := range []string{
		"http://www.youtube.com/watch?v=dQw4w9WgXcQ",
		"https://127.0.0.1/watch?v=dQw4w9WgXcQ",
		"https://www.youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
		"https://evil.com/watch?v=dQw4w9WgXcQ",
		"https://www.youtube.com:8080/watch?v=dQw4w9WgXcQ",
		"https://user:pass@www.youtube.com/watch?v=dQw4w9WgXcQ",
		"https://www.youtube.com/redirect?target=http%3A%2F%2F127.0.0.1",
		"https://www.youtube.com/watch?v=http://127.0.0.1/",
		"file:///etc/passwd", "--proxy", "dQw4w9WgXcQ/../../admin",
		"https://b23.tv/unsafe", "https://www.youtube.com/watch?v=dQw4w9WgXcQ#fragment",
	} {
		if got, err := canonicalMediaURL("auto", raw, false); err == nil {
			t.Errorf("unsafe input %q accepted: %s", raw, got)
		}
	}
	if _, err := canonicalMediaURL("auto", "dQw4w9WgXcQ", false); err == nil {
		t.Fatal("auto must not accept an unqualified identifier")
	}
	if _, err := canonicalMediaURL("youtube", "https://x.com/u/status/1234567890", false); err == nil {
		t.Fatal("mismatched platform must be rejected")
	}
}
