#!/usr/bin/env python3
"""Comprehensive Docker testing script."""

import asyncio
import aiohttp
import time
import subprocess
import sys
import json

async def test_docker_deployment():
    """Test the complete Docker deployment."""
    print("🐳 Docker Deployment Test")
    print("=" * 50)
    
    # Test endpoints
    base_url = "http://localhost:8000"
    
    tests = [
        # Basic functionality
        ("API Root", "GET", "/", None),
        ("Health Check", "GET", "/api/v2/system/health", None),
        ("OpenAPI Docs", "GET", "/docs", None),
        
        # Authentication system
        ("Auth Status", "GET", "/api/v2/auth/status", None),
        ("Auth Guide", "GET", "/api/v2/auth/guide", None),
        ("Instagram Auth Info", "GET", "/api/v2/auth/platforms/instagram", None),
        
        # Simple API endpoints
        ("Supported Platforms", "GET", "/api/platforms", None),
        ("YouTube Video Info", "GET", "/api/info?url=https://youtu.be/dQw4w9WgXcQ", None),
        ("Stream URL (JSON)", "GET", "/api/stream?url=https://youtu.be/dQw4w9WgXcQ&format=json", None),
        
        # System endpoints
        ("System Stats", "GET", "/api/v2/system/stats", None),
        ("Cache Stats", "GET", "/api/v2/stream/stats", None),
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for test_name, method, endpoint, expected_status in tests:
            try:
                start_time = time.time()
                url = f"{base_url}{endpoint}"
                
                async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    duration = time.time() - start_time
                    status = response.status
                    
                    # Determine success
                    if expected_status:
                        success = status == expected_status
                    else:
                        success = 200 <= status < 400
                    
                    if success:
                        try:
                            data = await response.json()
                            result = f"✅ {test_name}: {status} ({duration:.2f}s)"
                            
                            # Add specific info for key endpoints
                            if endpoint == "/":
                                result += f" - v{data.get('version', 'unknown')}"
                            elif "health" in endpoint:
                                result += f" - {data.get('status', 'unknown')}"
                            elif "youtube" in endpoint.lower() and "info" in endpoint:
                                info = data.get('info', {})
                                title = info.get('title', 'No title')[:40]
                                result += f" - {title}..."
                            elif "stream" in endpoint and "json" in endpoint:
                                result += f" - {data.get('platform', 'unknown')} stream"
                            elif "platforms" in endpoint:
                                total = data.get('total_platforms', 0)
                                result += f" - {total} platforms"
                                
                        except:
                            result = f"✅ {test_name}: {status} ({duration:.2f}s) - Non-JSON response"
                    else:
                        result = f"❌ {test_name}: {status} ({duration:.2f}s)"
                    
                    results.append((success, result))
                    
            except asyncio.TimeoutError:
                results.append((False, f"⏱️  {test_name}: Timeout (>15s)"))
            except Exception as e:
                error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
                results.append((False, f"💥 {test_name}: {error_msg}"))
    
    # Print results
    print("\n📊 Docker Test Results:")
    print("-" * 50)
    passed = sum(1 for success, _ in results if success)
    
    for success, result in results:
        print(result)
    
    print(f"\n🎯 Summary: {passed}/{len(tests)} tests passed")
    
    # Performance analysis
    if passed >= len(tests) * 0.8:  # 80% pass rate
        print("🎉 Docker deployment is working excellently!")
        print("🚀 Ready for production use!")
    elif passed >= len(tests) * 0.6:  # 60% pass rate
        print("⚠️  Docker deployment is mostly functional.")
        print("🔧 Some features may need attention.")
    else:
        print("❌ Docker deployment has issues.")
        print("🛠️  Check logs and configuration.")
    
    return passed, len(tests)

def check_docker_status():
    """Check Docker containers status."""
    print("🔍 Checking Docker Status...")
    print("-" * 30)
    
    try:
        # Check if containers are running
        result = subprocess.run(['docker-compose', 'ps'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("📋 Container Status:")
            print(result.stdout)
            
            # Check if services are up
            if "Up" in result.stdout:
                print("✅ Docker services are running")
                return True
            else:
                print("⚠️  Docker services may not be fully started")
                return False
        else:
            print("❌ Error checking Docker status")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️  Docker command timed out")
        return False
    except FileNotFoundError:
        print("❌ Docker Compose not found")
        return False
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

async def wait_for_docker_ready(max_wait=60):
    """Wait for Docker services to be ready."""
    print(f"⏳ Waiting for Docker services to be ready (max {max_wait}s)...")
    
    for attempt in range(max_wait):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/api/v2/system/health",
                                     timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Docker API is ready! Status: {data.get('status', 'unknown')}")
                        return True
        except:
            pass
        
        if attempt % 10 == 0:  # Print every 10 seconds
            print(f"   Still waiting... ({attempt + 1}s elapsed)")
        
        await asyncio.sleep(1)
    
    print(f"❌ Docker services did not become ready within {max_wait} seconds")
    return False

async def main():
    """Main Docker test function."""
    print("🐳" + "="*60 + "🐳")
    print("  YouTuberBilBiliHelper - Docker Deployment Test")
    print("🐳" + "="*60 + "🐳")
    
    # Check Docker status first
    docker_running = check_docker_status()
    
    if not docker_running:
        print("\n🚀 Starting Docker services...")
        try:
            result = subprocess.run(['docker-compose', 'up', '-d'], 
                                  timeout=300, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker services started successfully")
            else:
                print("❌ Failed to start Docker services")
                print(result.stderr)
                return
        except subprocess.TimeoutExpired:
            print("⏱️  Docker startup timed out (5 minutes)")
            return
        except Exception as e:
            print(f"💥 Error starting Docker: {e}")
            return
    
    # Wait for services to be ready
    if await wait_for_docker_ready():
        # Run comprehensive tests
        passed, total = await test_docker_deployment()
        
        print(f"\n🏆 Final Results:")
        print(f"   Tests Passed: {passed}/{total}")
        print(f"   Success Rate: {passed/total*100:.1f}%")
        print(f"   Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if passed == total:
            print("\n🎉 Perfect! Docker deployment is fully functional!")
        elif passed >= total * 0.8:
            print("\n🎯 Great! Docker deployment is working well!")
        else:
            print("\n⚠️  Docker deployment needs attention.")
    
    print("\n📋 Next Steps:")
    print("   • View logs: docker-compose logs")
    print("   • Stop services: docker-compose down")
    print("   • Rebuild: docker-compose build --no-cache")
    print("   • API docs: http://localhost:8000/docs")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Test failed: {e}")
        sys.exit(1)
