#!/usr/bin/env python3
"""Quick test script for the new streaming endpoints."""

import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"

async def test_endpoint(session, endpoint, description):
    """Test a single endpoint."""
    print(f"\n🧪 Testing: {description}")
    print(f"📡 Endpoint: {endpoint}")
    
    start_time = time.time()
    try:
        async with session.get(f"{BASE_URL}{endpoint}") as response:
            duration = time.time() - start_time
            
            if response.status == 200:
                print(f"✅ Success: {response.status} ({duration:.2f}s)")
                if 'application/json' in response.headers.get('content-type', ''):
                    data = await response.json()
                    print(f"📄 Response: {data}")
                else:
                    print(f"📄 Content-Type: {response.headers.get('content-type')}")
            elif response.status == 302:
                print(f"↗️  Redirect: {response.status} → {response.headers.get('location', 'N/A')} ({duration:.2f}s)")
            else:
                print(f"❌ Error: {response.status} ({duration:.2f}s)")
                text = await response.text()
                print(f"📄 Error: {text[:200]}...")
                
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 Exception: {str(e)} ({duration:.2f}s)")

async def main():
    """Run streaming endpoint tests."""
    print("🚀 Starting YouTuberBilBiliHelper Streaming Tests")
    print("=" * 60)
    
    # Test video ID (Rick Astley - Never Gonna Give You Up)
    test_video = "dQw4w9WgXcQ"
    
    async with aiohttp.ClientSession() as session:
        
        # Test basic health check
        await test_endpoint(session, "/api/v2/system/health", "System Health Check")
        
        # Test new streaming endpoints
        await test_endpoint(session, f"/api/v2/stream/info/youtube/{test_video}", "Stream Info")
        
        await test_endpoint(session, f"/api/v2/stream/direct/youtube/{test_video}?quality=720p", "Direct Stream (720p)")
        
        await test_endpoint(session, f"/api/v2/stream/auto/youtube/{test_video}?device=mobile", "Adaptive Stream")
        
        # Test URL-based streaming
        test_url = f"https://www.youtube.com/watch?v={test_video}"
        await test_endpoint(session, f"/api/v2/stream/url?url={test_url}", "URL-based Stream")
        
        # Test cache stats
        await test_endpoint(session, "/api/v2/stream/cache/stats", "Cache Statistics")
        
        # Test batch processing
        print(f"\n🧪 Testing: Batch Stream Processing")
        batch_data = [
            {"platform": "youtube", "video_id": test_video, "quality": "720p"},
            {"platform": "bilibili", "video_id": "BV1xx411c7mu", "quality": "best"}
        ]
        
        try:
            async with session.post(f"{BASE_URL}/api/v2/stream/batch", json=batch_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Batch Success: {data}")
                else:
                    print(f"❌ Batch Error: {response.status}")
        except Exception as e:
            print(f"💥 Batch Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
