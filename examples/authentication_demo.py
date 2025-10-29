#!/usr/bin/env python3
"""Demo showcasing the new authentication system."""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

def print_header(title):
    """Print formatted header."""
    print(f"\n🔐 {title}")
    print("=" * (len(title) + 4))

async def demo_auth_status():
    """Demo authentication status endpoint."""
    print_header("AUTHENTICATION STATUS")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v2/auth/status") as response:
            if response.status == 200:
                data = await response.json()
                
                print("📊 Authentication Overview:")
                summary = data['summary']
                print(f"   Total platforms: {summary['total_platforms']}")
                print(f"   Authenticated: {summary['authenticated_platforms']}")
                print(f"   With cookies: {summary['platforms_with_cookies']}")
                
                print(f"\n🔍 Platform Details:")
                for platform, status in data['auth_status'].items():
                    icon = "✅" if status['authenticated'] else "❌"
                    print(f"   {icon} {platform.upper():<10}: Auth={status['authenticated']}, Cookies={status['cookies_file']}")
            else:
                print(f"❌ Error: {response.status}")

async def demo_setup_guide():
    """Demo setup guide endpoint."""
    print_header("SETUP GUIDE & BENEFITS")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v2/auth/guide") as response:
            if response.status == 200:
                data = await response.json()
                
                print("💡 Authentication Benefits:")
                for platform, benefit in data['benefits'].items():
                    print(f"   🎯 {platform.upper():<10}: {benefit}")
                
                print(f"\n🛠️ Recommended Tools:")
                for ext in data['recommended_extensions']:
                    print(f"   • {ext}")
                
                print(f"\n📁 Cookie Files Location: {data['cookie_files_location']}")
                print(f"📄 Supported Formats: {', '.join(data['supported_formats'])}")
                
            else:
                print(f"❌ Error: {response.status}")

async def demo_platform_specific():
    """Demo platform-specific authentication info."""
    print_header("PLATFORM-SPECIFIC AUTHENTICATION")
    
    platforms = ["instagram", "twitter", "bilibili", "youtube", "twitch"]
    
    async with aiohttp.ClientSession() as session:
        for platform in platforms:
            print(f"\n🎥 {platform.upper()}:")
            
            async with session.get(f"{BASE_URL}/api/v2/auth/platforms/{platform}") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    auth = data['authentication']
                    print(f"   Status: {'✅ Enabled' if auth['enabled'] else '❌ Not configured'}")
                    print(f"   Priority: {data['priority']}")
                    print(f"   Benefit: {data['benefits']}")
                    print(f"   Expected file: {data['files']['expected_location']}")
                else:
                    print(f"   ❌ Error: {response.status}")

async def demo_template_creation():
    """Demo template creation."""
    print_header("TEMPLATE CREATION")
    
    async with aiohttp.ClientSession() as session:
        platform = "instagram"
        print(f"📝 Creating template for {platform}...")
        
        async with session.post(f"{BASE_URL}/api/v2/auth/template/{platform}") as response:
            if response.status == 200:
                data = await response.json()
                
                print(f"✅ {data['message']}")
                print(f"📁 Template file: {data['template_file']}")
                print(f"\n📋 Instructions:")
                for i, instruction in enumerate(data['instructions'], 1):
                    print(f"   {i}. {instruction}")
                print(f"\n💡 Next step: {data['next_step']}")
            else:
                print(f"❌ Error: {response.status}")

async def demo_authentication_impact():
    """Demo the impact of authentication on video extraction."""
    print_header("AUTHENTICATION IMPACT ON VIDEO EXTRACTION")
    
    print("🔍 Testing video extraction with current authentication status...")
    
    test_cases = [
        ("YouTube", "https://youtu.be/dQw4w9WgXcQ", "Should work without auth"),
        ("Instagram", "https://www.instagram.com/p/CwxQzVvSaAI/", "May fail without auth"),
        ("Twitter", "https://x.com/SpaceX/status/1234567890123456789", "May fail without auth")
    ]
    
    async with aiohttp.ClientSession() as session:
        for platform, url, expected in test_cases:
            print(f"\n🎬 {platform}: {expected}")
            print(f"   URL: {url}")
            
            try:
                async with session.get(
                    f"{BASE_URL}/api/info",
                    params={"url": url},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Success: {data['info']['title'][:50]}...")
                    else:
                        error_data = await response.json()
                        print(f"   ❌ Failed: {error_data.get('detail', 'Unknown error')[:50]}...")
                        
            except asyncio.TimeoutError:
                print(f"   ⏱️  Timeout (expected for some platforms)")
            except Exception as e:
                print(f"   💥 Error: {str(e)[:50]}...")

async def demo_auth_workflow():
    """Demo complete authentication workflow."""
    print_header("COMPLETE AUTHENTICATION WORKFLOW")
    
    print("📋 Step-by-step authentication setup:")
    
    workflow_steps = [
        ("1. Check Status", "GET /api/v2/auth/status", "See which platforms need auth"),
        ("2. Get Guide", "GET /api/v2/auth/guide", "Learn how to set up authentication"),
        ("3. Platform Info", "GET /api/v2/auth/platforms/{platform}", "Get platform-specific instructions"),
        ("4. Create Template", "POST /api/v2/auth/template/{platform}", "Generate cookie template file"),
        ("5. Manual Setup", "Browser + Extension", "Export cookies from logged-in browser"),
        ("6. Verify", "GET /api/v2/auth/status", "Confirm authentication is working"),
        ("7. Test", "GET /api/info?url=...", "Try extracting videos from authenticated platforms")
    ]
    
    for step, endpoint, description in workflow_steps:
        print(f"\n{step}: {endpoint}")
        print(f"   Purpose: {description}")
    
    print(f"\n💡 Pro Tips:")
    print(f"   • Start with Instagram (highest priority)")
    print(f"   • Use 'Get cookies.txt' browser extension")
    print(f"   • Keep cookies files secure and private")
    print(f"   • Restart API server after adding cookies")
    print(f"   • Check /api/v2/auth/status to verify setup")

async def demo_security_considerations():
    """Demo security considerations."""
    print_header("SECURITY CONSIDERATIONS")
    
    print("🛡️ Important Security Notes:")
    
    security_notes = [
        ("Cookie Files", "Contains login session data - keep secure"),
        ("File Permissions", "Set restrictive permissions (600) on cookie files"),
        ("Regular Updates", "Re-export cookies if login sessions expire"),
        ("Environment", "Don't commit cookie files to version control"),
        ("Access Control", "Limit access to config/cookies/ directory"),
        ("Monitoring", "Check auth status regularly for expired sessions")
    ]
    
    for category, note in security_notes:
        print(f"   🔒 {category}: {note}")
    
    print(f"\n⚠️  Cookie File Locations:")
    print(f"   📁 config/cookies/instagram_cookies.txt")
    print(f"   📁 config/cookies/twitter_cookies.txt") 
    print(f"   📁 config/cookies/bilibili_cookies.txt")
    
    print(f"\n✅ Best Practices:")
    print(f"   • Use dedicated accounts for API access")
    print(f"   • Enable 2FA on social media accounts")
    print(f"   • Rotate cookies periodically")
    print(f"   • Monitor for unusual activity")

async def main():
    """Run the authentication demo."""
    print("🔐" + "="*70 + "🔐")
    print("  YouTuberBilBiliHelper - Authentication System Demo")
    print("🔐" + "="*70 + "🔐")
    
    # Check server status
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
    
    # Run all demos
    await demo_auth_status()
    await demo_setup_guide()
    await demo_platform_specific()
    await demo_template_creation()
    await demo_authentication_impact()
    await demo_auth_workflow()
    await demo_security_considerations()
    
    print_header("🎯 AUTHENTICATION SYSTEM SUMMARY")
    
    print("   🚀 NEW FEATURES:")
    print("   ✅ Authentication status monitoring")
    print("   ✅ Platform-specific setup guides")
    print("   ✅ Cookie template generation")
    print("   ✅ Automatic auth integration with yt-dlp")
    print("   ✅ Security best practices")
    
    print("\n   📈 EXPECTED IMPROVEMENTS:")
    print("   🎯 Instagram: Significantly better success rate")
    print("   🎯 Twitter: Access to protected content")
    print("   🎯 BiliBili: Region-locked content access")
    print("   🎯 Overall: Fewer 'Video not found' errors")
    
    print("\n   🛠️ NEXT STEPS:")
    print("   1. Check auth status: curl http://localhost:8000/api/v2/auth/status")
    print("   2. Create templates: curl -X POST http://localhost:8000/api/v2/auth/template/instagram")
    print("   3. Set up cookies using browser extensions")
    print("   4. Restart API server and test improved extraction")
    
    print(f"\n🎉 Authentication system is ready to improve video extraction reliability!")

if __name__ == "__main__":
    asyncio.run(main())
