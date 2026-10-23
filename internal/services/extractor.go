package services

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"time"
)

const maxExtractOutput = 24 << 20 // 24 MiB per yt-dlp call, including playlists.
const extractorTimeout = 60 * time.Second

// Constrain the number of yt-dlp processes to avoid CPU/memory exhaustion.
var extractorSlots = make(chan struct{}, 4)

type boundedOutput struct {
	bytes.Buffer
	max int
	truncated bool
}

func (b *boundedOutput) Write(p []byte) (int, error) {
	n := len(p)
	remain := b.max - b.Len()
	if remain <= 0 {
		b.truncated = true
		return n, nil
	}
	if n > remain {
		_, _ = b.Buffer.Write(p[:remain])
		b.truncated = true
		return n, nil
	}
	_, _ = b.Buffer.Write(p)
	return n, nil
}

func (s *VideoService) runYtDLP(ctx context.Context, args []string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, extractorTimeout)
	defer cancel()
	select {
	case extractorSlots <- struct{}{}:
		defer func(){ <-extractorSlots }()
	case <-ctx.Done():
		return nil, ctx.Err()
	}
	cmd := exec.CommandContext(ctx, "yt-dlp", args...)
	cmd.WaitDelay = 2 * time.Second
	var stdout = &boundedOutput{max: maxExtractOutput}
	var stderr = &boundedOutput{max: 8192}
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	err := cmd.Run()
	if ctx.Err() != nil {
		return nil, fmt.Errorf("yt-dlp timed out or cancelled: %w", ctx.Err())
	}
	if stdout.truncated {
		return nil, errors.New("yt-dlp output exceeds 24 MiB limit")
	}
	if err != nil {
		return nil, fmt.Errorf("yt-dlp failed: %w (%s)", err, stderr.String())
	}
	return stdout.Bytes(), nil
}
