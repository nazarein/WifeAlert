import asyncio
import json
import os
import webbrowser
import aiohttp
from typing import Set
from config import Config
from utils.encryption import TokenEncryption
from core.twitch_monitor import TwitchMonitor
from core.chat import TwitchChat
from utils.paths import get_data_file, get_app_data_dir, get_asset_file


class WifeAlertMonitor(TwitchMonitor):
    def __init__(self, client_id: str, usernames: list[str]):
        super().__init__(client_id, usernames)
        self.notification_manager = None
        self.live_channels: Set[str] = set()
        self.emote_blacklist = set()
        self._emote_settings_cache = {}
        self._chat_settings_cache = None
        self._message_tasks = {}
        self.suppress_actions = False

    async def _get_emote_settings(self, username: str):
        try:
            emote_settings_path = get_data_file("emote_settings.json")
            if os.path.exists(emote_settings_path):
                with open(emote_settings_path, "r") as f:
                    self._emote_settings_cache = json.load(f)
                    return self._emote_settings_cache.get(username.lower())
            return None
        except Exception:
            return None

    async def handle_stream_up(
        self, channel_id: str, server_time: str, trigger_actions: bool = True
    ):
        try:
            username = next(
                (
                    name
                    for name, id_ in self.username_to_id.items()
                    if id_ == channel_id
                ),
                channel_id,
            )
            if channel_id in self.live_channels:
                return

            self.live_channels.add(channel_id)
            self.update_live_indicators()

            if trigger_actions and not self.suppress_actions:
                cache_dir = os.path.join(get_app_data_dir(), "assets", "profile_cache")
                profile_image = None
                username_lower = username.lower()
                for ext in [".jpg", ".png", ".jpeg"]:
                    possible_path = os.path.abspath(
                        os.path.join(cache_dir, f"{username_lower}{ext}")
                    )
                    if os.path.exists(possible_path):
                        profile_image = possible_path
                        break

                if self.notification_manager:
                    notification_title = f"🔴 {username} is Live!"
                    notification_message = f"{username} has started streaming"
                    await self.notification_manager.notify(
                        notification_title,
                        notification_message,
                        streamer_name=username,
                        profile_image=profile_image,
                    )

                    for i in range(
                        self.notification_manager.window.streamer_list.count()
                    ):
                        item = self.notification_manager.window.streamer_list.item(i)
                        widget = (
                            self.notification_manager.window.streamer_list.itemWidget(
                                item
                            )
                        )

                        if (
                            hasattr(widget, "streamer_name")
                            and widget.streamer_name.lower() == username.lower()
                        ):
                            if widget.open_checkbox.isChecked():
                                if (
                                    not self.notification_manager.window.prevent_open_checkbox.isChecked()
                                ):
                                    stream_url = f"https://twitch.tv/{username}"
                                    if hasattr(widget, "mod_view") and widget.mod_view:
                                        stream_url = f"https://www.twitch.tv/moderator/{username}"
                                    webbrowser.open(stream_url)

                            if widget.emote_checkbox.isChecked():
                                if channel_id in self.emote_blacklist:
                                    pass
                                else:
                                    if channel_id in self._message_tasks:
                                        existing_task = self._message_tasks[channel_id]
                                        if not existing_task.done():
                                            existing_task.cancel()

                                    async def send_messages():
                                        try:
                                            streamer_settings = (
                                                await self._get_emote_settings(username)
                                            )

                                            if (
                                                streamer_settings
                                                and streamer_settings.get("enabled")
                                                and streamer_settings.get("message")
                                            ):
                                                chat = TwitchChat()
                                                token_encryption = TokenEncryption()

                                                chat_settings_path = get_data_file(
                                                    "chat_login.json"
                                                )
                                                if os.path.exists(chat_settings_path):
                                                    with open(
                                                        chat_settings_path, "r"
                                                    ) as f:
                                                        chat_settings = json.load(f)
                                                        chat_username = (
                                                            chat_settings.get(
                                                                "username"
                                                            )
                                                        )
                                                        encrypted_oauth = (
                                                            chat_settings.get("oauth")
                                                        )

                                                    if (
                                                        chat_username
                                                        and encrypted_oauth
                                                    ):
                                                        oauth = token_encryption.decrypt_token(
                                                            encrypted_oauth
                                                        )
                                                        if await chat.ensure_connected(
                                                            chat_username, oauth
                                                        ):
                                                            message_lines = (
                                                                streamer_settings[
                                                                    "message"
                                                                ]
                                                                .strip()
                                                                .split("\n")
                                                            )
                                                            message_delay = (
                                                                streamer_settings.get(
                                                                    "message_delay", 1
                                                                )
                                                            )
                                                            initial_delay = (
                                                                streamer_settings.get(
                                                                    "initial_delay", 0
                                                                )
                                                            )

                                                            if initial_delay > 0:
                                                                await asyncio.sleep(
                                                                    initial_delay / 1000
                                                                )

                                                            for line in message_lines:
                                                                line = line.strip()
                                                                if line:
                                                                    success = await chat.send_message(
                                                                        username, line
                                                                    )
                                                                    if not success:
                                                                        break
                                                                    if (
                                                                        message_delay
                                                                        > 0
                                                                    ):
                                                                        await asyncio.sleep(
                                                                            message_delay
                                                                            / 1000
                                                                        )
                                        finally:
                                            if channel_id in self._message_tasks:
                                                del self._message_tasks[channel_id]

                                    task = asyncio.create_task(send_messages())
                                    self._message_tasks[channel_id] = task

                            break

                    self.emote_blacklist.add(channel_id)
                    asyncio.create_task(self.remove_from_blacklist(channel_id))
                    self.update_live_indicators()
        except Exception:
            pass

    async def remove_from_blacklist(self, channel_id: str):
        await asyncio.sleep(20)
        self.emote_blacklist.discard(channel_id)
        username = next(
            (name for name, id_ in self.username_to_id.items() if id_ == channel_id),
            channel_id,
        )

    async def handle_stream_down(self, channel_id: str):
        if channel_id in self.live_channels:
            self.live_channels.remove(channel_id)
            self.update_live_indicators()
            self.emote_blacklist.add(channel_id)
            asyncio.create_task(self.remove_from_blacklist(channel_id))

    _rate_limit_semaphore = asyncio.Semaphore(2)

    async def check_stream_status(self, username: str):
        async with self._rate_limit_semaphore:
            url = f"https://decapi.me/twitch/uptime/{username}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        text = await response.text()
                        is_live = not "offline" in text.lower()
                        channel_id = self.username_to_id.get(username.lower())
                        current_status = (
                            channel_id in self.live_channels if channel_id else False
                        )
                        return is_live
            except Exception:
                return False

    async def initialize(self):
        await super().initialize()
        try:
            self.live_channels.clear()
            currently_live = []

            status_tasks = [
                self.check_stream_status(username) for username in self.usernames
            ]
            results = await asyncio.gather(*status_tasks)

            for username, is_live in zip(self.usernames, results):
                if is_live:
                    currently_live.append(username)
                    channel_id = self.username_to_id.get(username)
                    if channel_id:
                        self.live_channels.add(channel_id)
                        await self.handle_stream_up(
                            channel_id, None, trigger_actions=False
                        )

            self.update_live_indicators()

            if currently_live and self.notification_manager:
                notification_title = "📺 Currently Live Streamers"
                notification_message = ", ".join(currently_live)
                app_icon = get_asset_file("icon.png")
                await self.notification_manager.notify(
                    notification_title,
                    notification_message,
                    streamer_name=None,
                    profile_image=app_icon,
                )
        except Exception:
            pass

    def update_live_indicators(self):
        if not hasattr(self, "notification_manager") or not self.notification_manager:
            return

        window = self.notification_manager.window
        if not window:
            return

        for i in range(window.streamer_list.count()):
            item = window.streamer_list.item(i)
            widget = window.streamer_list.itemWidget(item)
            if widget and hasattr(widget, "streamer_name"):
                channel_id = self.username_to_id.get(widget.streamer_name.lower())
                is_live = bool(channel_id and channel_id in self.live_channels)
                widget.set_live_status(is_live)
