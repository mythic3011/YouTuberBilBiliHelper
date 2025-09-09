#!/usr/bin/env python3
"""Quick test script to verify the API is working without Docker."""

import asyncio
import aiohttp
import time
import json

BASE_URL = "http://localhost:8000"

async def test_api():
    """Test the API endpoints quickly."""
    print("🚀 Quick API Test Starting...")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        tests = [
            ("Root Endpoint", "GET", "/"),
            ("Health Check", "GET", "/api/v2/system/health"),
            ("Auth Status", "GET", "/api/v2/auth/status"),
            ("Platforms", "GET", "/api/platforms"),
            ("YouTube Info", "GET", "/api/info?url=https://youtu.be/dQw4w9WgXcQ"),
            ("Stream URL", "GET", "/api/stream?url=https://youtu.be/dQw4w9WgXcQ&format=json"),
        ]
        
        results = []
        
        for test_name, method, endpoint in tests:
            try:
                start_time = time.time()
                url = f"{BASE_URL}{endpoint}"
                
                async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    duration = time.time() - start_time
                    status = response.status
                    
                    if status == 200:
                        data = await response.json()
                        result = f"✅ {test_name}: {status} ({duration:.2f}s)"
                        
                        # Show key info for some endpoints
                        if endpoint == "/":
                            result += f" - v{data.get('version', 'unknown')}"
                        elif "health" in endpoint:
                            result += f" - {data.get('status', 'unknown')}"
                        elif "youtube" in endpoint.lower():
                            info = data.get('info', {})
                            title = info.get('title', 'No title')[:30] + "..."
                            result += f" - {title}"
                            
                    else:
                        result = f"❌ {test_name}: {status} ({duration:.2f}s)"
                        
                    results.append((True, result))
                    
            except asyncio.TimeoutError:
                results.append((False, f"⏱️  {test_name}: Timeout"))
            except Exception as e:
                results.append((False, f"💥 {test_name}: Error - {str(e)[:50]}..."))
        
        # Print results
        print("\n📊 Test Results:")
        print("-" * 50)
        passed = 0
        for success, result in results:
            print(result)
            if success:
                passed += 1
        
        print(f"\n🎯 Summary: {passed}/{len(tests)} tests passed")
        
        if passed == len(tests):
            print("🎉 All tests passed! API is working correctly.")
        elif passed > len(tests) // 2:
            print("⚠️  Most tests passed. API is mostly functional.")
        else:
            print("❌ Many tests failed. Check if the server is running.")

async def test_docker_api():
    """Test the Docker API when it's ready."""
    print("\n🐳 Testing Docker API...")
    print("=" * 50)
    
    # Wait for Docker to be ready
    for attempt in range(30):  # Wait up to 30 seconds
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/api/v2/system/health", 
                                     timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        print("✅ Docker API is ready!")
                        await test_api()  # Run full test suite
                        return
        except:
            pass
        
        print(f"⏳ Waiting for Docker API... (attempt {attempt + 1}/30)")
        await asyncio.sleep(1)
    
    print("❌ Docker API did not start within 30 seconds")

def check_local_server():
    """Check if local server is running."""
    import socket
    try:
        sock = socket.create_connection(('localhost', 8000), timeout=1)
        sock.close()
        return True
    except:
        return False

async def main():
    """Main test function."""
    print("🔍 YouTuberBilBiliHelper - Quick Test Suite")
    print("=" * 60)
    
    if check_local_server():
        print("🟢 Local server detected on port 8000")
        await test_api()
    else:
        print("🔴 No local server detected on port 8000")
        print("💡 Options:")
        print("   1. Start local server: uvicorn app.main:app --reload")
        print("   2. Wait for Docker build to complete")
        print("   3. Run: docker-compose up")
    
    print(f"\n⏰ Test completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Test failed with error: {e}")
