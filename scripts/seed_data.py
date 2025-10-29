#!/usr/bin/env python3
"""
Seed test data for development and testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.redis_service import redis_service


async def seed_cache():
    """Seed Redis cache with test data."""
    print("🌱 Seeding cache data...")

    try:
        pool = await redis_service.get_pool()

        # Test video metadata
        test_videos = [
            {
                "key": "video:youtube:dQw4w9WgXcQ",
                "data": {
                    "id": "dQw4w9WgXcQ",
                    "title": "Rick Astley - Never Gonna Give You Up",
                    "platform": "youtube",
                    "duration": 212,
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                },
            },
            {
                "key": "video:bilibili:BV1xx411c7XD",
                "data": {
                    "id": "BV1xx411c7XD",
                    "title": "Test Bilibili Video",
                    "platform": "bilibili",
                    "duration": 300,
                    "thumbnail": "https://example.com/thumb.jpg",
                },
            },
        ]

        for video in test_videos:
            await pool.setex(
                video["key"],
                3600,  # 1 hour
                str(video["data"])
            )
            print(f"  ✓ Added: {video['data']['title']}")

        # Test statistics
        await pool.setex(
            "stats:downloads:total",
            3600,
            "42"
        )
        print("  ✓ Added: Download statistics")

        print("✅ Cache seeded successfully!")

    except Exception as e:
        print(f"❌ Error seeding cache: {e}")
        raise
    finally:
        await redis_service.close()


async def main():
    """Main entry point."""
    print("🌱 Starting data seeding...")
    print()

    await seed_cache()

    print()
    print("✅ All data seeded successfully!")
    print()
    print("You can now:")
    print("  • Test API endpoints")
    print("  • Run integration tests")
    print("  • Develop with realistic data")


if __name__ == "__main__":
    asyncio.run(main())
