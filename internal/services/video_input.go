package services

import (
	"errors"
	"fmt"
	"net/url"
	"regexp"
	"strings"
)

var (
	youtubeVideoPattern    = regexp.MustCompile("^[A-Za-z0-9_-]{11}$")
	youtubePlaylistPattern = regexp.MustCompile("^[A-Za-z0-9_-]{10,128}$")
	bilibiliVideoPattern   = regexp.MustCompile("^(BV[A-Za-z0-9]{10}|av[0-9]{1,20})$")
	numericVideoPattern    = regexp.MustCompile("^[0-9]{1,24}$")
	instagramVideoPattern  = regexp.MustCompile("^[A-Za-z0-9_-]{4,32}$")
)

// canonicalMediaURL turns supported platform IDs/URLs into a known provider
// URL. Never give yt-dlp an arbitrary caller-supplied URL or bare "auto" input.
// URLs are parsed only to extract identifiers; original URLs are never fetched.
func canonicalMediaURL(platform, raw string, playlist bool) (string, error) {
	platform = strings.ToLower(strings.TrimSpace(platform))
	raw = strings.TrimSpace(raw)
	if len(raw) == 0 || len(raw) > 2048 {
		return "", errors.New("invalid media identifier length")
	}
	mediaID := raw
	instagramKind := "p"
	if strings.Contains(raw, "://") {
		u, err := url.Parse(raw)
		if err != nil || u.Scheme != "https" || u.User != nil || u.Opaque != "" ||
			u.Host == "" || (u.Port() != "" && u.Port() != "443") || u.Fragment != "" {
			return "", errors.New("media URL must be HTTPS without credentials, a custom port or fragment")
		}
		host := strings.ToLower(u.Hostname())
		parts := strings.Split(strings.Trim(u.EscapedPath(), "/"), "/")
		pathID := func(prefix string) (string, bool) {
			if len(parts) == 2 && parts[0] == prefix {
				id, err := url.PathUnescape(parts[1])
				if err == nil && !strings.Contains(id, "/") {
					return id, true
				}
			}
			return "", false
		}
		detected, id, kind := "", "", ""
		switch host {
		case "www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com":
			detected = "youtube"
			if playlist {
				if u.Path == "/playlist" || u.Path == "/watch" {
					id = u.Query().Get("list")
				}
			} else if u.Path == "/watch" {
				id = u.Query().Get("v")
			} else {
				for _, prefix := range []string{"shorts", "live", "embed"} {
					if v, ok := pathID(prefix); ok {
						id = v
					}
				}
			}
		case "youtu.be":
			detected = "youtube"
			if !playlist && len(parts) == 1 {
				id, _ = url.PathUnescape(parts[0])
			}
		case "www.bilibili.com", "bilibili.com":
			detected = "bilibili"
			if !playlist {
				id, _ = pathID("video")
			}
		case "x.com", "www.x.com", "twitter.com", "www.twitter.com":
			detected = "twitter"
			if !playlist && len(parts) == 3 && parts[1] == "status" {
				id, _ = url.PathUnescape(parts[2])
			}
		case "instagram.com", "www.instagram.com":
			detected = "instagram"
			if !playlist {
				for _, prefix := range []string{"p", "reel", "tv"} {
					if v, ok := pathID(prefix); ok {
						id, kind = v, prefix
					}
				}
			}
		case "twitch.tv", "www.twitch.tv":
			detected = "twitch"
			if !playlist {
				id, _ = pathID("videos")
			}
		default:
			return "", errors.New("unsupported media URL host")
		}
		if id == "" {
			return "", errors.New("unsupported media URL path or missing identifier")
		}
		if platform != "auto" && platform != detected && !(platform == "x" && detected == "twitter") {
			return "", errors.New("media URL host does not match requested platform")
		}
		platform = detected
		mediaID = id
		if kind != "" {
			instagramKind = kind
		}
	}
	if strings.ContainsAny(mediaID, "/\\:?%#@ \t\r\n") || strings.Contains(mediaID, "..") {
		return "", errors.New("invalid media identifier")
	}
	switch platform {
	case "youtube":
		if playlist {
			if !youtubePlaylistPattern.MatchString(mediaID) {
				return "", errors.New("invalid YouTube playlist identifier")
			}
			return "https://www.youtube.com/playlist?list=" + url.QueryEscape(mediaID), nil
		}
		if youtubeVideoPattern.MatchString(mediaID) {
			return "https://www.youtube.com/watch?v=" + url.QueryEscape(mediaID), nil
		}
	case "bilibili":
		if !playlist && bilibiliVideoPattern.MatchString(mediaID) {
			return "https://www.bilibili.com/video/" + mediaID, nil
		}
	case "twitter", "x":
		if !playlist && numericVideoPattern.MatchString(mediaID) {
			return "https://twitter.com/i/status/" + mediaID, nil
		}
	case "instagram":
		if !playlist && instagramVideoPattern.MatchString(mediaID) {
			return fmt.Sprintf("https://www.instagram.com/%s/%s/", instagramKind, mediaID), nil
		}
	case "twitch":
		if !playlist && numericVideoPattern.MatchString(mediaID) {
			return "https://www.twitch.tv/videos/" + mediaID, nil
		}
	case "auto":
		return "", errors.New("auto requires a recognized full HTTPS media URL")
	}
	return "", errors.New("unsupported platform or invalid media identifier")
}
