"""Authentication service for platform-specific authentication."""

import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AuthService:
    """Handles authentication for various video platforms."""
    
    def __init__(self):
        self.auth_data = {}
        self.cookies_dir = Path("config/cookies")
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self._load_auth_config()
    
    def _load_auth_config(self):
        """Load authentication configuration."""
        try:
            config_file = Path("config/auth.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    self.auth_data = json.load(f)
                logger.info("Authentication configuration loaded")
            else:
                logger.info("No authentication configuration found")
        except Exception as e:
            logger.error(f"Failed to load auth config: {e}")
            
    def get_cookies_file(self, platform: str) -> Optional[str]:
        """Get cookies file path for platform."""
        cookies_file = self.cookies_dir / f"{platform}_cookies.txt"
        if cookies_file.exists():
            return str(cookies_file)
        return None
        
    def get_auth_headers(self, platform: str) -> Dict[str, str]:
        """Get authentication headers for platform."""
        headers = {}
        
        # Platform-specific headers
        if platform == "instagram":
            headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
        elif platform == "twitter":
            headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://twitter.com/'
            })
        elif platform == "bilibili":
            headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Accept': 'application/json, text/plain, */*'
            })
            
        return headers
        
    def get_yt_dlp_options(self, platform: str) -> Dict[str, Any]:
        """Get yt-dlp options with authentication for platform."""
        options = {}
        
        # Add cookies if available
        cookies_file = self.get_cookies_file(platform)
        if cookies_file:
            options['cookiefile'] = cookies_file
            logger.debug(f"Using cookies file for {platform}: {cookies_file}")
            
        # Add headers
        headers = self.get_auth_headers(platform)
        if headers:
            options['http_headers'] = headers
            
        # Platform-specific options
        if platform == "instagram":
            options.update({
                'extract_flat': False,
                'no_warnings': True,
                'ignoreerrors': True,
            })
        elif platform == "twitter":
            options.update({
                'extract_flat': False,
                'no_warnings': True,
                'ignoreerrors': True,
            })
        elif platform == "bilibili":
            options.update({
                'extract_flat': False,
                'no_warnings': True,
                'geo_bypass': True,
            })
            
        return options
        
    def is_auth_available(self, platform: str) -> bool:
        """Check if authentication is available for platform."""
        return (
            self.get_cookies_file(platform) is not None or
            platform in self.auth_data
        )
        
    def create_cookies_template(self, platform: str) -> str:
        """Create a cookies template file for manual setup."""
        template_content = f"""# Cookies for {platform.title()}
# 
# To use authentication with {platform.title()}:
# 1. Install a browser extension like "Get cookies.txt" or "cookies.txt"
# 2. Log in to {platform}.com in your browser
# 3. Export cookies and save them in this file
# 4. Restart the API server
#
# Format: Netscape HTTP Cookie File
# This is a generated file! Do not edit.

"""
        
        template_file = self.cookies_dir / f"{platform}_cookies_template.txt"
        with open(template_file, 'w') as f:
            f.write(template_content)
            
        return str(template_file)
        
    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all platforms."""
        platforms = ["youtube", "bilibili", "instagram", "twitter", "twitch"]
        status = {}
        
        for platform in platforms:
            status[platform] = {
                "authenticated": self.is_auth_available(platform),
                "cookies_file": self.get_cookies_file(platform) is not None,
                "has_config": platform in self.auth_data
            }
            
        return status
        
    def setup_auth_guide(self) -> Dict[str, str]:
        """Generate setup guide for authentication."""
        guide = {
            "instagram": """
1. Install browser extension 'Get cookies.txt' or similar
2. Log in to Instagram in your browser
3. Export cookies to config/cookies/instagram_cookies.txt
4. Restart the API server
5. Instagram videos should now work more reliably
            """,
            "twitter": """
1. Install browser extension 'Get cookies.txt' or similar  
2. Log in to Twitter/X in your browser
3. Export cookies to config/cookies/twitter_cookies.txt
4. Restart the API server
5. Twitter videos should now work more reliably
            """,
            "bilibili": """
1. Install browser extension 'Get cookies.txt' or similar
2. Log in to BiliBili in your browser
3. Export cookies to config/cookies/bilibili_cookies.txt
4. Restart the API server
5. BiliBili videos should now work more reliably
            """,
            "general": """
Authentication improves reliability for platforms that require login:
- Instagram: Required for most posts
- Twitter: Required for some videos
- BiliBili: Required for some regions/videos
- YouTube: Generally works without auth
- Twitch: Generally works without auth
            """
        }
        
        return guide


# Global auth service instance
auth_service = AuthService()
