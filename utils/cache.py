import os
import aiohttp
from utils.paths import get_app_data_dir


class ImageCache:
    def __init__(self):
        self.cache_dir = os.path.join(get_app_data_dir(), "assets", "profile_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    async def download_image(self, url: str, username: str) -> str:
        """Download image and return path to cached file"""
        try:
            file_ext = os.path.splitext(url)[1] or ".jpg"
            cache_path = os.path.join(self.cache_dir, f"{username}{file_ext}")

            if os.path.exists(cache_path):
                return cache_path

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(cache_path, "wb") as f:
                            f.write(await response.read())

                        return cache_path

            return None

        except Exception:
            pass
