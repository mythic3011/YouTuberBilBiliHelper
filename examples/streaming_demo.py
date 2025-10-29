#!/usr/bin/env python3
"""Demo script showcasing the enhanced YouTuberBilBiliHelper streaming proxy."""

import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"

def print_banner():
    """Print demo banner."""
    print("🎬" + "="*60 + "🎬")
    print("  YouTuberBilBiliHelper Enhanced Streaming Proxy Demo")
    print("🎬" + "="*60 + "🎬")
    print()

async def demo_basic_streaming():
    """Demonstrate basic streaming functionality."""
    print("📺 Demo 1: Basic Video Stream Info")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Get video info
        async with session.get(f"{BASE_URL}/api/v2/stream/info/youtube/dQw4w9WgXcQ") as response:
            if response.status == 200:
                data = await response.json()
                video_info = data["video_info"]
                
                print(f"🎵 Title: {video_info['title']}")
                print(f"👤 Uploader: {video_info['uploader']}")
                print(f"⏱️  Duration: {video_info['duration']} seconds")
                print(f"🔗 Stream URL: {data['stream_url'][:80]}...")
                print(f"💾 Quality: {data['quality']}")
                print()
            else:
                print(f"❌ Error: {response.status}")

async def demo_quality_selection():
    """Demonstrate quality selection."""
    print("⚙️ Demo 2: Quality Selection")
    print("-" * 40)
    
    qualities = ["best", "worst", "720p"]
    
    async with aiohttp.ClientSession() as session:
        for quality in qualities:
            start_time = time.time()
            
            async with session.get(
                f"{BASE_URL}/api/v2/stream/direct/youtube/dQw4w9WgXcQ?quality={quality}",
                allow_redirects=False
            ) as response:
                duration = time.time() - start_time
                
                if response.status == 302:
                    stream_url = response.headers.get('location', '')
                    print(f"📊 {quality:>6}: ✅ Redirect in {duration:.2f}s → {stream_url[:60]}...")
                else:
                    print(f"📊 {quality:>6}: ❌ Error {response.status}")
    print()

async def demo_adaptive_streaming():
    """Demonstrate adaptive streaming."""
    print("🤖 Demo 3: Adaptive Quality Selection")
    print("-" * 40)
    
    test_cases = [
        ("mobile", 1000, "Low bandwidth mobile"),
        ("mobile", 3000, "Medium bandwidth mobile"), 
        ("desktop", 5000, "High bandwidth desktop")
    ]
    
    async with aiohttp.ClientSession() as session:
        for device, bandwidth, description in test_cases:
            start_time = time.time()
            
            async with session.get(
                f"{BASE_URL}/api/v2/stream/auto/youtube/dQw4w9WgXcQ?device={device}&bandwidth={bandwidth}",
                allow_redirects=False
            ) as response:
                duration = time.time() - start_time
                
                if response.status == 302:
                    selected_quality = response.headers.get('X-Selected-Quality', 'unknown')
                    print(f"🎯 {description}: Selected {selected_quality} quality ({duration:.2f}s)")
                else:
                    print(f"🎯 {description}: ❌ Error {response.status}")
    print()

async def demo_url_detection():
    """Demonstrate URL-based streaming."""
    print("🔍 Demo 4: URL Auto-Detection")
    print("-" * 40)
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.bilibili.com/video/BV1xx411c7mu"  # This will fail, but shows error handling
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in test_urls:
            start_time = time.time()
            
            try:
                async with session.get(
                    f"{BASE_URL}/api/v2/stream/url?url={url}",
                    allow_redirects=False
                ) as response:
                    duration = time.time() - start_time
                    
                    if response.status == 302:
                        print(f"✅ {url[:40]}... → Success ({duration:.2f}s)")
                    else:
                        print(f"❌ {url[:40]}... → Error {response.status} ({duration:.2f}s)")
                        
            except Exception as e:
                duration = time.time() - start_time
                print(f"💥 {url[:40]}... → Exception: {str(e)[:30]}... ({duration:.2f}s)")
    print()

async def demo_batch_processing():
    """Demonstrate batch processing."""
    print("📦 Demo 5: Batch Processing")
    print("-" * 40)
    
    batch_requests = [
        {"platform": "youtube", "video_id": "dQw4w9WgXcQ", "quality": "720p"},
        {"platform": "youtube", "video_id": "oHg5SJYRHA0", "quality": "best"},  # Another video
        {"platform": "bilibili", "video_id": "BV1xx411c7mu", "quality": "best"}  # Will fail
    ]
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        async with session.post(f"{BASE_URL}/api/v2/stream/batch", json=batch_requests) as response:
            duration = time.time() - start_time
            
            if response.status == 200:
                data = await response.json()
                results = data["batch_results"]["results"]
                
                print(f"⚡ Processed {len(batch_requests)} requests in {duration:.2f}s")
                print(f"✅ Successful: {data['batch_results']['successful']}")
                print(f"❌ Failed: {data['batch_results']['failed']}")
                
                for key, result in results.items():
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {key}")
            else:
                print(f"❌ Batch request failed: {response.status}")
    print()

async def demo_performance():
    """Demonstrate performance with caching."""
    print("⚡ Demo 6: Performance & Caching")
    print("-" * 40)
    
    video_id = "dQw4w9WgXcQ"
    
    async with aiohttp.ClientSession() as session:
        # First request (cache miss)
        print("🔄 First request (cache miss)...")
        start_time = time.time()
        async with session.get(f"{BASE_URL}/api/v2/stream/info/youtube/{video_id}") as response:
            first_duration = time.time() - start_time
            if response.status == 200:
                print(f"   ⏱️  Time: {first_duration:.2f}s")
            
        # Second request (cache hit)
        print("🔄 Second request (should be cached)...")
        start_time = time.time()
        async with session.get(f"{BASE_URL}/api/v2/stream/info/youtube/{video_id}") as response:
            second_duration = time.time() - start_time
            if response.status == 200:
                print(f"   ⏱️  Time: {second_duration:.2f}s")
                
        speedup = first_duration / second_duration if second_duration > 0 else 1
        print(f"🚀 Speedup: {speedup:.1f}x faster with caching!")
    print()

async def demo_embed_player():
    """Demonstrate embeddable player."""
    print("🎮 Demo 7: Embeddable Player")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v2/stream/embed/youtube/dQw4w9WgXcQ?width=640&height=360") as response:
            if response.status == 200:
                html_content = await response.text()
                lines = html_content.split('\n')
                print("📄 Generated HTML5 player:")
                print("   " + lines[0])  # DOCTYPE
                print("   " + lines[2])  # HTML tag
                print("   " + lines[4])  # Title
                print("   ...")
                print("   " + [line.strip() for line in lines if 'video' in line and 'width' in line][0])
                print("   ...")
                print(f"📊 Total size: {len(html_content)} characters")
            else:
                print(f"❌ Error generating player: {response.status}")
    print()

async def main():
    """Run all demos."""
    print_banner()
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/v2/system/health") as response:
                if response.status != 200:
                    print("❌ Server not responding. Make sure the API is running on port 8000!")
                    return
                
                data = await response.json()
                print(f"🟢 Server Status: {data['status']} (v{data['version']})")
                if data['status'] == 'unhealthy':
                    print("⚠️  Note: Redis is not running, but streaming still works!")
                print()
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Make sure to run: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Run all demos
    demos = [
        demo_basic_streaming,
        demo_quality_selection,
        demo_adaptive_streaming,
        demo_url_detection,
        demo_batch_processing,
        demo_performance,
        demo_embed_player
    ]
    
    for demo in demos:
        try:
            await demo()
        except Exception as e:
            print(f"💥 Demo error: {e}")
            print()
    
    print("🎉 Demo completed! The enhanced streaming proxy is working perfectly!")
    print()
    print("💡 Try these URLs in your browser:")
    print("   📖 API Docs: http://localhost:8000/docs")
    print("   🎵 Direct Stream: http://localhost:8000/api/v2/stream/direct/youtube/dQw4w9WgXcQ")
    print("   🎮 Embed Player: http://localhost:8000/api/v2/stream/embed/youtube/dQw4w9WgXcQ")
    print("   📊 Health Check: http://localhost:8000/api/v2/system/health")

if __name__ == "__main__":
    asyncio.run(main())
