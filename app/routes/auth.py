"""Authentication management routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.services.auth_service import auth_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/auth", tags=["Authentication"])


@router.get("/status")
async def get_auth_status():
    """
    Get authentication status for all platforms.
    
    Returns information about which platforms have authentication
    configured and available.
    """
    try:
        status = auth_service.get_auth_status()
        return {
            "auth_status": status,
            "summary": {
                "total_platforms": len(status),
                "authenticated_platforms": sum(1 for p in status.values() if p["authenticated"]),
                "platforms_with_cookies": sum(1 for p in status.values() if p["cookies_file"])
            },
            "timestamp": "2025-09-09T19:30:00Z"
        }
    except Exception as e:
        logger.error(f"Error getting auth status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get authentication status")


@router.get("/guide")
async def get_setup_guide():
    """
    Get setup guide for authentication.
    
    Returns detailed instructions on how to set up authentication
    for each platform to improve video extraction reliability.
    """
    try:
        guide = auth_service.setup_auth_guide()
        return {
            "setup_guide": guide,
            "cookie_files_location": "config/cookies/",
            "supported_formats": ["Netscape HTTP Cookie File (.txt)"],
            "recommended_extensions": [
                "Get cookies.txt (Chrome/Firefox)",
                "cookies.txt (Chrome)", 
                "Cookie-Editor (Chrome/Firefox)"
            ],
            "benefits": {
                "instagram": "Access to private/protected posts and stories",
                "twitter": "Access to protected tweets and better rate limits", 
                "bilibili": "Access to region-locked content and better quality",
                "general": "Improved success rate and fewer 'Video not found' errors"
            }
        }
    except Exception as e:
        logger.error(f"Error getting setup guide: {e}")
        raise HTTPException(status_code=500, detail="Failed to get setup guide")


@router.post("/template/{platform}")
async def create_cookies_template(platform: str):
    """
    Create a cookies template file for a platform.
    
    Creates a template file with instructions for manually
    setting up cookies for the specified platform.
    """
    supported_platforms = ["instagram", "twitter", "bilibili", "youtube", "twitch"]
    
    if platform.lower() not in supported_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' not supported. Supported: {supported_platforms}"
        )
    
    try:
        template_file = auth_service.create_cookies_template(platform.lower())
        return {
            "message": f"Template created for {platform}",
            "template_file": template_file,
            "instructions": [
                f"1. Log in to {platform}.com in your browser",
                "2. Install a cookies export browser extension",
                "3. Export cookies to the template file location",
                "4. Rename from '_template.txt' to '.txt'",
                "5. Restart the API server"
            ],
            "next_step": f"Replace the template file with actual cookies from {platform}.com"
        }
    except Exception as e:
        logger.error(f"Error creating template for {platform}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")


@router.get("/platforms/{platform}")
async def get_platform_auth_info(platform: str):
    """
    Get detailed authentication information for a specific platform.
    
    Returns authentication status, available options, and specific
    setup instructions for the requested platform.
    """
    supported_platforms = ["instagram", "twitter", "bilibili", "youtube", "twitch"]
    
    if platform.lower() not in supported_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' not supported. Supported: {supported_platforms}"
        )
    
    try:
        status = auth_service.get_auth_status()
        platform_status = status.get(platform.lower(), {})
        
        guide = auth_service.setup_auth_guide()
        platform_guide = guide.get(platform.lower(), "No specific guide available")
        
        cookies_file = auth_service.get_cookies_file(platform.lower())
        
        return {
            "platform": platform.lower(),
            "authentication": {
                "enabled": platform_status.get("authenticated", False),
                "cookies_available": platform_status.get("cookies_file", False),
                "config_available": platform_status.get("has_config", False)
            },
            "files": {
                "cookies_file": cookies_file,
                "expected_location": f"config/cookies/{platform.lower()}_cookies.txt"
            },
            "setup_guide": platform_guide.strip(),
            "benefits": {
                "instagram": "Access to private posts, stories, and better reliability",
                "twitter": "Access to protected tweets and improved success rate",
                "bilibili": "Access to region-locked content and higher quality streams",
                "youtube": "Generally works without authentication", 
                "twitch": "Generally works without authentication"
            }.get(platform.lower(), "Improved reliability and success rate"),
            "priority": {
                "instagram": "High - Required for most content",
                "twitter": "Medium - Helpful for protected content", 
                "bilibili": "Medium - Helpful for region-locked content",
                "youtube": "Low - Usually not needed",
                "twitch": "Low - Usually not needed"
            }.get(platform.lower(), "Medium")
        }
    except Exception as e:
        logger.error(f"Error getting platform auth info for {platform}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get platform authentication info")


@router.delete("/cookies/{platform}")
async def remove_platform_cookies(platform: str):
    """
    Remove cookies for a specific platform.
    
    Deletes the cookies file for the specified platform,
    effectively disabling authentication for that platform.
    """
    supported_platforms = ["instagram", "twitter", "bilibili", "youtube", "twitch"]
    
    if platform.lower() not in supported_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' not supported. Supported: {supported_platforms}"
        )
    
    try:
        cookies_file = auth_service.get_cookies_file(platform.lower())
        
        if not cookies_file:
            return {
                "message": f"No cookies file found for {platform}",
                "platform": platform.lower(),
                "action": "none_required"
            }
        
        # Remove the cookies file
        import os
        os.remove(cookies_file)
        
        return {
            "message": f"Cookies removed for {platform}",
            "platform": platform.lower(), 
            "removed_file": cookies_file,
            "action": "cookies_deleted",
            "note": "Restart the API server to apply changes"
        }
        
    except Exception as e:
        logger.error(f"Error removing cookies for {platform}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove cookies")
