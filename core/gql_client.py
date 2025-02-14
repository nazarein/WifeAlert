"""
GraphQL client for Twitch API interactions. Handles user lookups, channel info retrieval,
and profile image caching. Implements rate limiting and connection management for
reliable API communication.
"""

from typing import Dict, Any, List
import os
import json
import aiohttp
import asyncio
from config import Config
from utils.cache import ImageCache
from utils.paths import get_data_file


class GQLClient:
    """
    Client for making GraphQL requests to Twitch's API. Features:
    - Username to channel ID resolution
    - Profile image caching
    - Rate limiting for API requests
    - Connection pooling and timeout handling
    - Persistent cache for channel IDs
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.headers = {
            "Client-ID": self.client_id,
            "Content-Type": "application/json",
        }
        self.image_cache = ImageCache()
        self._rate_limit_semaphore = asyncio.Semaphore(10)

    async def lookup_usernames(self, usernames: List[str]) -> Dict[str, str]:
        """
        Resolves Twitch usernames to their channel IDs. Uses cached values when available
        and fetches new ones from the API when needed. Also downloads and caches profile
        images for new users.

        Args:
            usernames: List of Twitch usernames to look up

        Returns:
            Dict mapping lowercase usernames to their channel IDs
        """
        username_to_id = {}
        usernames_to_lookup = []

        try:
            filepath = get_data_file("streamers.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    data = json.load(f)
                    stored_ids = data.get("channel_ids", {})

                    for username in usernames:
                        if username.lower() in stored_ids:
                            username_to_id[username.lower()] = stored_ids[
                                username.lower()
                            ]
                        else:
                            usernames_to_lookup.append(username)
            else:
                usernames_to_lookup = usernames
        except Exception:
            usernames_to_lookup = usernames

        if usernames_to_lookup:
            query = {
                "operationName": "GetUserID",
                "variables": {"login": None},
                "query": """
                    query GetUserID($login: String!) {
                        user(login: $login) {
                            id
                            login
                            displayName
                            profileImageURL(width: 300)
                        }
                    }
                """,
            }

            for username in usernames_to_lookup:
                try:
                    async with self._rate_limit_semaphore:
                        username_lower = username.lower()
                        has_cached_image = False
                        for ext in [".jpg", ".png", ".jpeg"]:
                            if os.path.exists(
                                os.path.join(
                                    self.image_cache.cache_dir, f"{username_lower}{ext}"
                                )
                            ):
                                has_cached_image = True
                                break

                        query["variables"]["login"] = username

                        # SSL verification bypass for packaged executable
                        async with aiohttp.ClientSession(
                            connector=aiohttp.TCPConnector(ssl=False)
                        ) as session:
                            async with session.post(
                                Config.GQL_ENDPOINT,
                                headers=self.headers,
                                json=query,
                                timeout=Config.REQUEST_TIMEOUT,
                            ) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    user_data = data.get("data", {}).get("user")

                                    if user_data and user_data.get("id"):
                                        username_to_id[username.lower()] = user_data[
                                            "id"
                                        ]

                                        if not has_cached_image:
                                            if profile_url := user_data.get(
                                                "profileImageURL"
                                            ):
                                                try:
                                                    await self.image_cache.download_image(
                                                        profile_url, username.lower()
                                                    )
                                                except Exception:
                                                    pass

                    await asyncio.sleep(0.1)

                except Exception:
                    continue

        return username_to_id

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """
        Fetches detailed channel information from Twitch's GraphQL API.
        Retrieves current stream status, viewer count, game info, and profile data.

        Args:
            channel_id: Twitch channel ID to look up

        Returns:
            Dict containing channel information or empty dict on error
        """
        query = {
            "operationName": "GetChannelInfo",
            "query": """
                query GetChannelInfo($id: ID!) {
                    user(id: $id) {
                        id
                        login
                        displayName
                        profileImageURL(width: 300)
                        stream {
                            id
                            title
                            viewersCount
                            game {
                                name
                            }
                        }
                    }
                }
            """,
            "variables": {"id": channel_id},
        }

        try:
            async with self._rate_limit_semaphore:
                # SSL verification bypass for packaged executable
                async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=False)
                ) as session:
                    async with session.post(
                        Config.GQL_ENDPOINT,
                        headers=self.headers,
                        json=query,
                        timeout=Config.REQUEST_TIMEOUT,
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            return {}
        except Exception:
            return {}
