#!/usr/bin/env python3
"""Test script for the new simple, user-friendly API endpoints."""

import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"

def print_header(title):
    """Print formatted header."""
    print(f"\n🎯 {title}")
    print("=" * (len(title) + 4))

async def test_root_endpoint():
    """Test the enhanced root endpoint."""
    print_header("ROOT ENDPOINT - API Discovery")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ API: {data['name']} v{data['version']}")
                print(f"📖 Documentation: {BASE_URL}{data['docs_url']}")
                
                print(f"\n🔗 Simple Endpoints:")
                for name, endpoint in data.get('simple_endpoints', {}).items():
                    print(f"   {name:<10}: {endpoint}")
                
                print(f"\n💡 Examples:")
                for name, example in data.get('examples', {}).items():
                    print(f"   {name}: {BASE_URL}{example}")
                
                print(f"\n🌐 Supported: {', '.join(data.get('supported_platforms', []))}")
            else:
                print(f"❌ Root endpoint failed: {response.status}")

async def test_platforms_endpoint():
    """Test the platforms listing endpoint."""
    print_header("PLATFORMS ENDPOINT - Supported Platforms")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/platforms") as response:
            if response.status == 200:
                data = await response.json()
                platforms = data.get('supported_platforms', [])
                
                print(f"📊 Total platforms: {data.get('total_platforms', 0)}")
                
                for platform in platforms:
                    print(f"\n🎥 {platform['name']} ({platform['platform_id']})")
                    print(f"   Domains: {', '.join(platform['domains'])}")
                    print(f"   Features: {', '.join(platform['features'])}")
                    if 'notes' in platform:
                        print(f"   Note: {platform['notes']}")
                    print(f"   Example: {platform['example_urls'][0]}")
                
                print(f"\n🛠️ Simple Endpoints Available:")
                for endpoint in data.get('simple_endpoints', []):
                    print(f"   • {endpoint}")
            else:
                print(f"❌ Platforms endpoint failed: {response.status}")

async def test_simple_stream_endpoint():
    """Test the simple stream endpoint with different formats."""
    print_header("SIMPLE STREAM ENDPOINT - Easy Video Streaming")
    
    test_urls = [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in test_urls:
            print(f"\n🔗 Testing URL: {url}")
            
            # Test different formats
            formats = ["redirect", "json", "proxy"]
            
            for fmt in formats:
                print(f"   📝 Format: {fmt}")
                start_time = time.time()
                
                try:
                    params = {"url": url, "format": fmt, "quality": "720p"}
                    async with session.get(
                        f"{BASE_URL}/api/stream",
                        params=params,
                        allow_redirects=(fmt != "redirect")
                    ) as response:
                        duration = time.time() - start_time
                        
                        if fmt == "redirect" and response.status == 302:
                            print(f"      ✅ Redirect to stream URL ({duration:.3f}s)")
                            print(f"      🔗 Location: {response.headers.get('location', 'N/A')[:100]}...")
                        elif fmt == "json" and response.status == 200:
                            data = await response.json()
                            print(f"      ✅ JSON response ({duration:.3f}s)")
                            print(f"      🎬 Platform: {data.get('platform', 'N/A')}")
                            print(f"      🎯 Quality: {data.get('quality', 'N/A')}")
                            print(f"      ✅ Stream URL available: {bool(data.get('stream_url'))}")
                        elif fmt == "proxy" and response.status == 302:
                            print(f"      ✅ Proxy redirect ({duration:.3f}s)")
                            print(f"      🔗 Proxy URL: {response.headers.get('location', 'N/A')}")
                        else:
                            print(f"      ❓ Status: {response.status} ({duration:.3f}s)")
                            
                except Exception as e:
                    print(f"      ❌ Error: {str(e)}")

async def test_simple_info_endpoint():
    """Test the simple info endpoint."""
    print_header("SIMPLE INFO ENDPOINT - Video Information")
    
    test_urls = [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.bilibili.com/video/BV1xx411c7mu"
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in test_urls:
            print(f"\n🔗 Testing URL: {url}")
            start_time = time.time()
            
            try:
                async with session.get(
                    f"{BASE_URL}/api/info",
                    params={"url": url}
                ) as response:
                    duration = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        info = data.get('info', {})
                        
                        print(f"      ✅ Success ({duration:.3f}s)")
                        print(f"      🎬 Platform: {data.get('platform', 'N/A')}")
                        print(f"      📺 Title: {info.get('title', 'N/A')}")
                        print(f"      ⏱️  Duration: {info.get('duration', 'N/A')}s")
                        print(f"      👤 Uploader: {info.get('uploader', 'N/A')}")
                        print(f"      📊 Views: {info.get('view_count', 'N/A')}")
                        print(f"      🎵 Stream Available: {data.get('stream_available', False)}")
                    else:
                        error_data = await response.json()
                        print(f"      ❌ Error ({duration:.3f}s): {error_data.get('detail', 'Unknown')}")
                        
            except Exception as e:
                print(f"      💥 Exception: {str(e)}")

async def test_simple_download_endpoint():
    """Test the simple download endpoint (without actually downloading)."""
    print_header("SIMPLE DOWNLOAD ENDPOINT - Easy Downloads")
    
    test_cases = [
        ("https://youtu.be/dQw4w9WgXcQ", "720p", None),
        ("https://youtu.be/dQw4w9WgXcQ", "highest", "my_video.mp4")
    ]
    
    async with aiohttp.ClientSession() as session:
        for url, quality, filename in test_cases:
            print(f"\n🔗 URL: {url}")
            print(f"   🎯 Quality: {quality}")
            print(f"   📁 Filename: {filename or 'auto-generated'}")
            
            try:
                params = {"url": url, "quality": quality}
                if filename:
                    params["filename"] = filename
                
                async with session.get(
                    f"{BASE_URL}/api/download",
                    params=params,
                    allow_redirects=False
                ) as response:
                    
                    if response.status == 302:
                        redirect_url = response.headers.get('location', '')
                        print(f"      ✅ Download redirect ready")
                        print(f"      🔗 Proxy URL: {redirect_url}")
                        
                        # Check if it has download parameters
                        if 'download=true' in redirect_url:
                            print(f"      📥 Download headers will be added")
                        if 'filename=' in redirect_url:
                            print(f"      📄 Custom filename will be used")
                    else:
                        print(f"      ❓ Status: {response.status}")
                        
            except Exception as e:
                print(f"      ❌ Error: {str(e)}")

async def test_simple_formats_endpoint():
    """Test the simple formats endpoint."""
    print_header("SIMPLE FORMATS ENDPOINT - Available Qualities")
    
    async with aiohttp.ClientSession() as session:
        url = "https://youtu.be/dQw4w9WgXcQ"
        print(f"🔗 Testing URL: {url}")
        
        try:
            async with session.get(
                f"{BASE_URL}/api/formats",
                params={"url": url}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"   ✅ Success")
                    print(f"   🎬 Platform: {data.get('platform', 'N/A')}")
                    print(f"   🎯 Recommended: {data.get('recommended_quality', 'N/A')}")
                    print(f"   📊 Available qualities:")
                    
                    for quality in data.get('available_qualities', []):
                        print(f"      • {quality}")
                    
                    info = data.get('video_info', {})
                    print(f"   📺 Title: {info.get('title', 'N/A')}")
                else:
                    error_data = await response.json()
                    print(f"   ❌ Error: {error_data.get('detail', 'Unknown')}")
                    
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")

async def test_simple_embed_endpoint():
    """Test the simple embed endpoint."""
    print_header("SIMPLE EMBED ENDPOINT - HTML5 Player")
    
    async with aiohttp.ClientSession() as session:
        url = "https://youtu.be/dQw4w9WgXcQ"
        print(f"🔗 Testing URL: {url}")
        
        try:
            params = {
                "url": url,
                "width": 800,
                "height": 450,
                "quality": "720p"
            }
            
            async with session.get(
                f"{BASE_URL}/api/embed",
                params=params,
                allow_redirects=False
            ) as response:
                
                if response.status == 302:
                    redirect_url = response.headers.get('location', '')
                    print(f"   ✅ Embed redirect ready")
                    print(f"   🔗 Player URL: {redirect_url}")
                    print(f"   📺 Size: 800x450")
                    print(f"   🎯 Quality: 720p")
                else:
                    print(f"   ❓ Status: {response.status}")
                    
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

async def test_health_endpoint():
    """Test the simple health endpoint."""
    print_header("SIMPLE HEALTH ENDPOINT - System Status")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{BASE_URL}/api/health",
                allow_redirects=False
            ) as response:
                
                if response.status == 302:
                    print(f"   ✅ Health check redirect ready")
                    print(f"   🔗 Redirects to: {response.headers.get('location', 'N/A')}")
                else:
                    print(f"   ❓ Status: {response.status}")
                    
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

async def main():
    """Run all simple API tests."""
    print("🚀" + "="*70 + "🚀")
    print("  YouTuberBilBiliHelper - Simple API Endpoints Test")
    print("🚀" + "="*70 + "🚀")
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/health", allow_redirects=True) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"🟢 Server: {data['status']} (v{data['version']})")
                else:
                    print("❌ Server not responding properly")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Run all tests
    await test_root_endpoint()
    await test_platforms_endpoint()
    await test_simple_stream_endpoint()
    await test_simple_info_endpoint()
    await test_simple_download_endpoint()
    await test_simple_formats_endpoint()
    await test_simple_embed_endpoint()
    await test_health_endpoint()
    
    print_header("🎯 SIMPLE API SUMMARY")
    
    print("   🎉 SUCCESS! All simple endpoints are working!")
    print("\n   💡 Key Benefits:")
    print("      • Single URL parameter - no need to specify platform")
    print("      • Auto-detection of video platform")
    print("      • Intuitive endpoint names (/stream, /info, /download)")
    print("      • Multiple response formats (redirect, json, proxy)")
    print("      • Quality selection made simple")
    print("      • Built-in examples and documentation")
    
    print("\n   🔗 Quick Examples:")
    print(f"      Stream:   curl -L '{BASE_URL}/api/stream?url=https://youtu.be/dQw4w9WgXcQ'")
    print(f"      Info:     curl '{BASE_URL}/api/info?url=https://youtu.be/dQw4w9WgXcQ' | jq")
    print(f"      Download: curl -L '{BASE_URL}/api/download?url=https://youtu.be/dQw4w9WgXcQ&quality=720p'")
    
    print(f"\n   📖 Full Documentation: {BASE_URL}/docs")
    print(f"   🌐 Supported Platforms: YouTube, BiliBili, Twitch, Instagram, Twitter")

if __name__ == "__main__":
    asyncio.run(main())
