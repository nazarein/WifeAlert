from typing import Dict, Any, List
import os
import json
import aiohttp
import asyncio
from config import Config
from utils.cache import ImageCache
from utils.paths import get_data_file


class GQLClient:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.headers = {
            "Client-ID": self.client_id,
            "Content-Type": "application/json",
        }
        self.image_cache = ImageCache()
        self._rate_limit_semaphore = asyncio.Semaphore(10)

    async def lookup_usernames(self, usernames: List[str]) -> Dict[str, str]:
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

                        # Create session with SSL verification disabled
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
                # Create session with SSL verification disabled
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
