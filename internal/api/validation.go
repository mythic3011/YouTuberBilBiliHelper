package api

import (
	"fmt"
	"regexp"
	"strings"

	"video-streaming-api/internal/config"
)

// ValidationError represents a validation failure with details.
type ValidationError struct {
	Field   string `json:"field"`
	Value   string `json:"value,omitempty"`
	Message string `json:"message"`
	Code    string `json:"code"`
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

// InputValidator defines the interface for validating user inputs.
type InputValidator interface {
	ValidatePlatform(platform string) error
	ValidateVideoID(videoID string) error
	ValidatePlaylistID(playlistID string) error
	ValidateQuality(quality string) error
	ValidateCountryCode(code string) error
	ValidateMode(mode string) error
}

// DefaultInputValidator implements InputValidator with configurable rules.
type DefaultInputValidator struct {
	allowedPlatforms    map[string]bool
	allowedQualities    map[string]bool
	maxVideoIDLength    int
	maxPlaylistIDLength int
}

// videoIDPattern matches alphanumeric, hyphens, underscores, and URL-safe characters.
var videoIDPattern = regexp.MustCompile(`^[a-zA-Z0-9_\-]+$`)

// countryCodePattern matches valid 2-letter ISO country codes.
var countryCodePattern = regexp.MustCompile(`^[A-Z]{2}$`)

// NewDefaultInputValidator creates a new validator with the given security config.
func NewDefaultInputValidator(cfg *config.SecurityConfig) *DefaultInputValidator {
	platforms := make(map[string]bool)
	for _, p := range cfg.AllowedPlatforms {
		platforms[strings.ToLower(p)] = true
	}

	qualities := make(map[string]bool)
	for _, q := range cfg.AllowedQualities {
		qualities[strings.ToLower(q)] = true
	}

	return &DefaultInputValidator{
		allowedPlatforms:    platforms,
		allowedQualities:    qualities,
		maxVideoIDLength:    cfg.MaxVideoIDLength,
		maxPlaylistIDLength: cfg.MaxPlaylistIDLength,
	}
}


// ValidatePlatform checks if the platform is in the allowed platforms list.
// Requirements: 1.1
func (v *DefaultInputValidator) ValidatePlatform(platform string) error {
	if platform == "" {
		return &ValidationError{
			Field:   "platform",
			Value:   platform,
			Message: "platform is required",
			Code:    "REQUIRED",
		}
	}

	normalized := strings.ToLower(strings.TrimSpace(platform))
	if !v.allowedPlatforms[normalized] {
		return &ValidationError{
			Field:   "platform",
			Value:   platform,
			Message: "unsupported platform",
			Code:    "INVALID_PLATFORM",
		}
	}

	return nil
}

// ValidateVideoID checks if the video ID contains only allowed characters and is within length limits.
// Requirements: 1.2
func (v *DefaultInputValidator) ValidateVideoID(videoID string) error {
	if videoID == "" {
		return &ValidationError{
			Field:   "video_id",
			Value:   videoID,
			Message: "video_id is required",
			Code:    "REQUIRED",
		}
	}

	if len(videoID) > v.maxVideoIDLength {
		return &ValidationError{
			Field:   "video_id",
			Value:   videoID,
			Message: fmt.Sprintf("video_id exceeds maximum length of %d characters", v.maxVideoIDLength),
			Code:    "MAX_LENGTH_EXCEEDED",
		}
	}

	if !videoIDPattern.MatchString(videoID) {
		return &ValidationError{
			Field:   "video_id",
			Value:   videoID,
			Message: "video_id contains invalid characters; only alphanumeric, hyphens, and underscores are allowed",
			Code:    "INVALID_CHARACTERS",
		}
	}

	return nil
}

// ValidatePlaylistID checks if the playlist ID contains only allowed characters and is within length limits.
// Requirements: 1.4
func (v *DefaultInputValidator) ValidatePlaylistID(playlistID string) error {
	if playlistID == "" {
		return &ValidationError{
			Field:   "playlist_id",
			Value:   playlistID,
			Message: "playlist_id is required",
			Code:    "REQUIRED",
		}
	}

	if len(playlistID) > v.maxPlaylistIDLength {
		return &ValidationError{
			Field:   "playlist_id",
			Value:   playlistID,
			Message: fmt.Sprintf("playlist_id exceeds maximum length of %d characters", v.maxPlaylistIDLength),
			Code:    "MAX_LENGTH_EXCEEDED",
		}
	}

	if !videoIDPattern.MatchString(playlistID) {
		return &ValidationError{
			Field:   "playlist_id",
			Value:   playlistID,
			Message: "playlist_id contains invalid characters; only alphanumeric, hyphens, and underscores are allowed",
			Code:    "INVALID_CHARACTERS",
		}
	}

	return nil
}

// ValidateQuality checks if the quality is in the allowed qualities list.
// Requirements: 1.3
func (v *DefaultInputValidator) ValidateQuality(quality string) error {
	if quality == "" {
		// Quality is optional, defaults to "best"
		return nil
	}

	normalized := strings.ToLower(strings.TrimSpace(quality))
	if !v.allowedQualities[normalized] {
		return &ValidationError{
			Field:   "quality",
			Value:   quality,
			Message: "unsupported quality value",
			Code:    "INVALID_QUALITY",
		}
	}

	return nil
}

// ValidateCountryCode checks if the country code is a valid 2-letter ISO code.
// Requirements: 1.5
func (v *DefaultInputValidator) ValidateCountryCode(code string) error {
	if code == "" {
		// Country code is optional
		return nil
	}

	normalized := strings.ToUpper(strings.TrimSpace(code))
	if !countryCodePattern.MatchString(normalized) {
		return &ValidationError{
			Field:   "country",
			Value:   code,
			Message: "country must be a valid 2-letter ISO country code",
			Code:    "INVALID_COUNTRY_CODE",
		}
	}

	return nil
}

// ValidateMode checks if the mode is either "proxy" or "direct".
// Requirements: 1.6
func (v *DefaultInputValidator) ValidateMode(mode string) error {
	if mode == "" {
		// Mode is optional
		return nil
	}

	normalized := strings.ToLower(strings.TrimSpace(mode))
	if normalized != "proxy" && normalized != "direct" {
		return &ValidationError{
			Field:   "mode",
			Value:   mode,
			Message: "mode must be either 'proxy' or 'direct'",
			Code:    "INVALID_MODE",
		}
	}

	return nil
}
