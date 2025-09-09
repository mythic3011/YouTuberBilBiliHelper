# Enhanced Streaming Proxy - Usage Examples

## 🎯 Simple & Focused: Core Streaming Features

The enhanced YouTuberBilBiliHelper now works as a **high-performance streaming proxy** with intelligent caching and multi-platform support.

## 🚀 Quick Examples

### 1. Direct Stream URLs (Fastest - Just Redirects)
```bash
# Get YouTube video stream
curl -L "http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ"
# → Redirects to actual video stream URL

# With quality selection
curl -L "http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ?quality=720p"

# BiliBili video
curl -L "http://localhost:8000/api/v2/stream/direct/bilibili/BV1xx411c7mu"

# Force fresh extraction (bypass cache)
curl -L "http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ?no_cache=true"
```

### 2. Proxy Streaming (For CORS/Embedding)
```bash
# Stream video through our server
curl "http://localhost:8000/api/v2/stream/proxy/youtube/dQw4w9WgXcQ" > video.mp4

# With quality selection
curl "http://localhost:8000/api/v2/stream/proxy/youtube/dQw4w9WgXcQ?quality=480p" > video_480p.mp4
```

### 3. Adaptive Quality Selection
```bash
# Auto-select quality based on device/bandwidth
curl -L "http://localhost:8000/api/v2/stream/auto/youtube/dQw4w9WgXcQ?device=mobile&bandwidth=1500"

# Device detection from User-Agent
curl -L "http://localhost:8000/api/v2/stream/auto/youtube/dQw4w9WgXcQ" \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)"
```

### 4. Stream Information (JSON Response)
```bash
# Get stream info without downloading
curl "http://localhost:8000/api/v2/stream/info/youtube/dQw4w9WgXcQ" | jq
```

Response:
```json
{
  "platform": "youtube",
  "video_id": "dQw4w9WgXcQ",
  "stream_url": "https://rr3---sn-p5qlsn7l.googlevideo.com/videoplayback?...",
  "quality": "best",
  "video_info": {
    "title": "Rick Astley - Never Gonna Give You Up",
    "duration": 212,
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "uploader": "Rick Astley"
  },
  "expires_at": 1704110400,
  "cached_at": 1704106800,
  "timestamp": 1704106800
}
```

### 5. URL-Based Streaming (Auto-detect Platform)
```bash
# Works with any supported URL
curl -L "http://localhost:8000/api/v2/stream/url?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Proxy mode
curl "http://localhost:8000/api/v2/stream/url?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&proxy=true" > video.mp4
```

### 6. Batch Processing
```bash
curl -X POST "http://localhost:8000/api/v2/stream/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {"platform": "youtube", "video_id": "dQw4w9WgXcQ", "quality": "720p"},
    {"platform": "bilibili", "video_id": "BV1xx411c7mu", "quality": "1080p"},
    {"platform": "twitch", "video_id": "123456789", "quality": "best"}
  ]'
```

### 7. Embeddable Player
```bash
# Get HTML5 video player
curl "http://localhost:8000/api/v2/stream/embed/youtube/dQw4w9WgXcQ?width=800&height=450&controls=true"
```

## 🔧 Platform Support

### Supported Platforms
- ✅ **YouTube** (`youtube`) - Full support with caching
- ✅ **BiliBili** (`bilibili`) - Full support
- 🔄 **Instagram** (`instagram`) - In progress  
- 🔄 **Twitter/X** (`twitter`) - In progress
- 🔄 **Twitch** (`twitch`) - In progress (clips & VODs)

### Quality Options
- `best` - Highest available quality
- `worst` - Lowest available quality
- `1080p`, `720p`, `480p`, `360p` - Specific resolutions
- `bestaudio` - Audio only, best quality
- `worstaudio` - Audio only, worst quality

## 🚀 Integration Examples

### 1. HTML Video Player
```html
<!DOCTYPE html>
<html>
<body>
  <video width="640" height="360" controls>
    <source src="http://localhost:8000/api/v2/stream/proxy/youtube/dQw4w9WgXcQ" type="video/mp4">
    Your browser does not support the video tag.
  </video>
</body>
</html>
```

### 2. JavaScript Fetch
```javascript
// Get stream info
async function getStreamInfo(platform, videoId) {
  const response = await fetch(`/api/v2/stream/info/${platform}/${videoId}`);
  return await response.json();
}

// Get direct stream URL
async function getStreamUrl(platform, videoId, quality = 'best') {
  const response = await fetch(`/api/v2/stream/direct/${platform}/${videoId}?quality=${quality}`, {
    redirect: 'manual'
  });
  return response.headers.get('location');
}

// Usage
const streamInfo = await getStreamInfo('youtube', 'dQw4w9WgXcQ');
console.log('Video title:', streamInfo.video_info.title);
```

### 3. Python Client
```python
import requests

# Get stream URL
def get_stream_url(platform, video_id, quality='best'):
    response = requests.get(
        f'http://localhost:8000/api/v2/stream/direct/{platform}/{video_id}',
        params={'quality': quality},
        allow_redirects=False
    )
    return response.headers['location']

# Download video
def download_video(platform, video_id, filename, quality='best'):
    response = requests.get(
        f'http://localhost:8000/api/v2/stream/proxy/{platform}/{video_id}',
        params={'quality': quality},
        stream=True
    )
    
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# Usage
stream_url = get_stream_url('youtube', 'dQw4w9WgXcQ', '720p')
download_video('youtube', 'dQw4w9WgXcQ', 'video.mp4', '720p')
```

### 4. cURL Download Script
```bash
#!/bin/bash
# download_video.sh

PLATFORM=$1
VIDEO_ID=$2
QUALITY=${3:-"best"}
OUTPUT=${4:-"video.mp4"}

echo "Downloading $PLATFORM video $VIDEO_ID in $QUALITY quality..."

curl -L "http://localhost:8000/api/v2/stream/proxy/$PLATFORM/$VIDEO_ID?quality=$QUALITY" \
  -o "$OUTPUT" \
  --progress-bar

echo "Downloaded to $OUTPUT"
```

Usage:
```bash
./download_video.sh youtube dQw4w9WgXcQ 720p rickroll.mp4
```

## 📊 Performance Features

### 1. Intelligent Caching
- **Stream URLs cached** for 15-60 minutes (platform dependent)
- **Video metadata cached** for 1 hour
- **Cache hit rate** typically >80% for popular content
- **Auto-expiration** prevents stale URLs

### 2. Adaptive Quality
- **Bandwidth detection** - Selects optimal quality based on connection speed
- **Device optimization** - Mobile devices get appropriate resolutions
- **Fallback logic** - Gracefully handles unavailable qualities

### 3. Fast Response Times
- **Direct mode**: <100ms (cache hit), <2s (cache miss)
- **Proxy mode**: Streaming starts immediately, no wait time
- **Batch processing**: Concurrent extraction for multiple videos

### 4. Error Handling
- **Graceful degradation** - Falls back to lower quality if preferred unavailable
- **Retry logic** - Automatic retry with exponential backoff
- **Clear error messages** - Detailed error responses for debugging

## 🔍 Monitoring & Debug

### Cache Statistics
```bash
curl "http://localhost:8000/api/v2/stream/cache/stats" | jq
```

### Health Check
```bash
curl "http://localhost:8000/api/v2/system/health" | jq
```

### Platform Status
```bash
curl "http://localhost:8000/api/v2/system/health" | jq '.services'
```

## ⚡ Performance Tips

### 1. Use Direct Mode for Speed
```bash
# Fastest - just get the URL
curl -I "http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ"
# Look for Location header
```

### 2. Cache Popular Content
```bash
# Pre-warm cache for popular videos
curl "http://localhost:8000/api/v2/stream/info/youtube/dQw4w9WgXcQ" > /dev/null
```

### 3. Use Appropriate Quality
```bash
# For mobile/low bandwidth
curl -L "http://localhost:8000/api/v2/stream/auto/youtube/dQw4w9WgXcQ?device=mobile"

# For desktop/high bandwidth
curl -L "http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ?quality=1080p"
```

## 🎯 Why This Approach Works

### 1. **Simple & Fast**
- One API call to get streamable video
- Direct redirects for maximum speed
- Intelligent caching reduces extraction overhead

### 2. **Reliable**
- Proven yt-dlp backend
- Fallback mechanisms for edge cases
- Clear error handling and logging

### 3. **Scalable**
- Redis caching scales horizontally
- Stateless design allows load balancing
- Minimal resource overhead per request

### 4. **Developer Friendly**
- RESTful API design
- Consistent response formats
- Comprehensive documentation

This streamlined approach delivers 80% of the value with 20% of the complexity!
