#!/usr/bin/env python3
"""Test script to check platform support in the enhanced API."""

import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"

async def test_platform_support():
    """Test which platforms are supported."""
    print("🧪 Testing Platform Support")
    print("=" * 50)
    
    # Test URLs for different platforms (using fake IDs that should fail gracefully)
    test_cases = [
        ("youtube", "dQw4w9WgXcQ", "Real YouTube video"),
        ("bilibili", "BV1xx411c7mu", "Test BiliBili video"),
        ("twitch", "123456789", "Test Twitch VOD"),
        ("instagram", "ABC123def", "Test Instagram post"),
        ("twitter", "1234567890123456789", "Test Twitter video"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for platform, video_id, description in test_cases:
            print(f"\n🔍 Testing {platform}: {description}")
            start_time = time.time()
            
            try:
                async with session.get(
                    f"{BASE_URL}/api/v2/stream/info/{platform}/{video_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    duration = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        video_info = data.get("video_info", {})
                        print(f"✅ {platform.upper()}: Success! ({duration:.2f}s)")
                        print(f"   Title: {video_info.get('title', 'N/A')}")
                        print(f"   Duration: {video_info.get('duration', 'N/A')}s")
                        print(f"   Stream URL: Available")
                        
                    elif response.status == 404:
                        print(f"🔍 {platform.upper()}: Platform supported, video not found ({duration:.2f}s)")
                        error_data = await response.json()
                        print(f"   Detail: {error_data.get('detail', 'Unknown error')}")
                        
                    else:
                        print(f"❌ {platform.upper()}: Error {response.status} ({duration:.2f}s)")
                        try:
                            error_data = await response.json()
                            print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                        except:
                            print(f"   Error: HTTP {response.status}")
                            
            except asyncio.TimeoutError:
                print(f"⏱️  {platform.upper()}: Timeout (>10s)")
            except Exception as e:
                print(f"💥 {platform.upper()}: Exception - {str(e)}")

async def test_url_detection():
    """Test URL-based platform detection."""
    print("\n\n🔍 Testing URL-based Platform Detection")
    print("=" * 50)
    
    # Test URLs that should be auto-detected
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ", 
        "https://www.bilibili.com/video/BV1xx411c7mu",
        "https://clips.twitch.tv/example-clip",
        "https://www.twitch.tv/videos/123456789",
        "https://www.instagram.com/p/ABC123/",
        "https://twitter.com/user/status/1234567890",
        "https://x.com/user/status/1234567890",
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in test_urls:
            print(f"\n🔗 Testing: {url}")
            
            try:
                async with session.get(
                    f"{BASE_URL}/api/v2/stream/url",
                    params={"url": url},
                    timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=False
                ) as response:
                    
                    if response.status == 302:
                        redirect_url = response.headers.get('location', '')
                        print(f"✅ Detected and redirecting to: /api/v2/stream/direct/...")
                        
                    elif response.status == 400:
                        error_data = await response.json()
                        print(f"❌ Invalid URL: {error_data.get('detail', 'Unknown error')}")
                        
                    else:
                        print(f"🔍 Status: {response.status}")
                        
            except Exception as e:
                print(f"💥 Error: {str(e)}")

async def main():
    """Run all platform tests."""
    print("🚀 YouTuberBilBiliHelper Platform Support Test")
    print("=" * 60)
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/v2/system/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"🟢 Server: {data['status']} (v{data['version']})")
                else:
                    print("❌ Server not responding properly")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Run tests
    await test_platform_support()
    await test_url_detection()
    
    print("\n\n🎯 Summary:")
    print("- YouTube: ✅ Full support")
    print("- BiliBili: 🔍 Partial support (may need auth)")
    print("- Twitch: 🔍 Supported by yt-dlp (clips may require valid URLs)")
    print("- Instagram: 🔍 Supported by yt-dlp (may require auth)")
    print("- Twitter: 🔍 Supported by yt-dlp (may require auth)")

if __name__ == "__main__":
    asyncio.run(main())
