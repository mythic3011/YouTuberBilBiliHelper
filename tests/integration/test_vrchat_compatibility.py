#!/usr/bin/env python3
"""
VRChat Compatibility Test Script

This script tests the VRChat-specific endpoints and features to ensure
they work correctly and provide the expected optimizations.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - classic test video
    "https://youtu.be/dQw4w9WgXcQ",  # Short YouTube URL
]

async def test_vrchat_stream_endpoint(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    """Test the VRChat-optimized stream endpoint."""
    print(f"\n🎮 Testing VRChat Stream Endpoint with: {url}")
    
    endpoint = f"{BASE_URL}/api/vrchat/stream"
    params = {"url": url, "quality": "720p"}
    
    try:
        async with session.get(endpoint, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Stream endpoint successful")
                print(f"   Platform: {data.get('platform', 'unknown')}")
                print(f"   Quality: {data.get('quality', 'unknown')}")
                print(f"   VRChat Optimized: {data.get('vrchat_optimized', False)}")
                print(f"   Stream URL: {data.get('stream_url', 'N/A')[:50]}...")
                return {"success": True, "data": data}
            else:
                error_text = await response.text()
                print(f"❌ Stream endpoint failed: {response.status}")
                print(f"   Error: {error_text}")
                return {"success": False, "error": error_text}
    except Exception as e:
        print(f"❌ Stream endpoint exception: {str(e)}")
        return {"success": False, "error": str(e)}

async def test_vrchat_info_endpoint(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    """Test the VRChat-optimized info endpoint."""
    print(f"\n📋 Testing VRChat Info Endpoint with: {url}")
    
    endpoint = f"{BASE_URL}/api/vrchat/info"
    params = {"url": url}
    
    try:
        async with session.get(endpoint, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Info endpoint successful")
                print(f"   Platform: {data.get('platform', 'unknown')}")
                print(f"   Title: {data.get('info', {}).get('title', 'N/A')[:50]}...")
                print(f"   Duration: {data.get('info', {}).get('duration', 'N/A')} seconds")
                print(f"   VRChat Compatible: {data.get('vrchat_compatible', False)}")
                print(f"   Compatibility Notes: {len(data.get('compatibility_notes', []))} notes")
                print(f"   Recommended Quality: {data.get('recommended_quality', 'N/A')}")
                
                # Show compatibility notes if any
                notes = data.get('compatibility_notes', [])
                if notes:
                    print("   Notes:")
                    for note in notes:
                        print(f"     - {note}")
                
                return {"success": True, "data": data}
            else:
                error_text = await response.text()
                print(f"❌ Info endpoint failed: {response.status}")
                print(f"   Error: {error_text}")
                return {"success": False, "error": error_text}
    except Exception as e:
        print(f"❌ Info endpoint exception: {str(e)}")
        return {"success": False, "error": str(e)}

async def test_filename_sanitization():
    """Test filename sanitization logic."""
    print(f"\n🧹 Testing Filename Sanitization")
    
    # Import the video service to test sanitization
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from app.services.video_service import VideoService
        
        video_service = VideoService()
        
        test_cases = [
            ("Rick's Amazing Video.mp4", "Ricks_Amazing_Video.mp4"),
            ("Video with \"quotes\" and 'apostrophes'", "Video_with_quotes_and_apostrophes"),
            ("Special!@#$%^&*()Characters", "SpecialCharacters"),
            ("Multiple   Spaces", "Multiple_Spaces"),
            ("", "video"),  # Empty string fallback
        ]
        
        print("Test cases:")
        all_passed = True
        for input_name, expected in test_cases:
            result = video_service._sanitize_filename_for_vrchat(input_name)
            passed = result == expected
            all_passed = all_passed and passed
            status = "✅" if passed else "❌"
            print(f"   {status} '{input_name}' → '{result}' (expected: '{expected}')")
        
        return {"success": all_passed}
        
    except ImportError as e:
        print(f"❌ Could not import video service: {e}")
        return {"success": False, "error": str(e)}

async def test_api_health(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Test if the API is running and healthy."""
    print(f"\n❤️ Testing API Health")
    
    endpoint = f"{BASE_URL}/api/health"
    
    try:
        async with session.get(endpoint, allow_redirects=True) as response:
            if response.status == 200:
                print(f"✅ API is healthy and running")
                return {"success": True}
            else:
                print(f"❌ API health check failed: {response.status}")
                return {"success": False, "error": f"Status {response.status}"}
    except Exception as e:
        print(f"❌ Could not reach API: {str(e)}")
        print(f"   Make sure the API server is running on {BASE_URL}")
        return {"success": False, "error": str(e)}

async def main():
    """Run all VRChat compatibility tests."""
    print("🎮 VRChat Compatibility Test Suite")
    print("=" * 50)
    
    results = {
        "health": None,
        "stream_tests": [],
        "info_tests": [],
        "sanitization": None
    }
    
    # Test filename sanitization (doesn't require API)
    results["sanitization"] = await test_filename_sanitization()
    
    # Create HTTP session for API tests
    async with aiohttp.ClientSession() as session:
        # Test API health first
        results["health"] = await test_api_health(session)
        
        if results["health"]["success"]:
            # Test VRChat endpoints with different URLs
            for test_url in TEST_URLS:
                stream_result = await test_vrchat_stream_endpoint(session, test_url)
                info_result = await test_vrchat_info_endpoint(session, test_url)
                
                results["stream_tests"].append(stream_result)
                results["info_tests"].append(info_result)
        else:
            print("\n⚠️ Skipping API tests due to health check failure")
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    # Health check
    health_status = "✅ PASS" if results["health"] and results["health"]["success"] else "❌ FAIL"
    print(f"API Health: {health_status}")
    
    # Sanitization test
    sanitization_status = "✅ PASS" if results["sanitization"]["success"] else "❌ FAIL"
    print(f"Filename Sanitization: {sanitization_status}")
    
    # Stream tests
    stream_passes = sum(1 for r in results["stream_tests"] if r["success"])
    stream_total = len(results["stream_tests"])
    print(f"VRChat Stream Tests: {stream_passes}/{stream_total} passed")
    
    # Info tests
    info_passes = sum(1 for r in results["info_tests"] if r["success"])
    info_total = len(results["info_tests"])
    print(f"VRChat Info Tests: {info_passes}/{info_total} passed")
    
    # Overall result
    all_tests = [results["health"], results["sanitization"]] + results["stream_tests"] + results["info_tests"]
    successful_tests = [t for t in all_tests if t and t.get("success", False)]
    total_tests = len([t for t in all_tests if t is not None])
    
    print(f"\nOverall: {len(successful_tests)}/{total_tests} tests passed")
    
    if len(successful_tests) == total_tests:
        print("🎉 All VRChat compatibility tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
