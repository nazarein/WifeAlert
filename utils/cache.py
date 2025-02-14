"""
Profile image caching system for Twitch streamers. Handles downloading
and local storage of profile images to reduce API requests and improve
load times. Supports SSL verification bypass for packaged executables.
"""

import os
import sys
import aiohttp
from utils.paths import get_app_data_dir


class ImageCache:
    """
    Manages local caching of Twitch profile images. Features:
    - Automatic cache directory creation
    - SSL-aware download handling
    - File extension preservation
    - Duplicate download prevention
    """

    def __init__(self):
        self.cache_dir = os.path.join(get_app_data_dir(), "assets", "profile_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    async def download_image(self, url: str, username: str) -> str:
        """
        Downloads and caches a streamer's profile image.
        Creates cache directory if needed and preserves file extension.
        Handles SSL verification based on execution context.

        Args:
            url: Profile image URL to download
            username: Streamer's username for filename

        Returns:
            str: Path to cached image file, or None on failure
        """
        try:
            file_ext = os.path.splitext(url)[1] or ".jpg"
            cache_path = os.path.join(self.cache_dir, f"{username}{file_ext}")

            if os.path.exists(cache_path):
                return cache_path

            connector = aiohttp.TCPConnector(
                ssl=False if getattr(sys, "frozen", False) else None
            )
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(cache_path, "wb") as f:
                            f.write(await response.read())

                        return cache_path

            return None

        except Exception:
            pass
