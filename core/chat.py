import socket
import asyncio
from typing import Optional, Set
from utils.error_handler import (
    handle_invalid_oauth,
    handle_chat_connection_error,
)


class TwitchChat:
    _instance = None
    _connected = False
    _current_oauth = None
    _current_username = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TwitchChat, cls).__new__(cls)
            cls._instance.server = "irc.chat.twitch.tv"
            cls._instance.port = 6667
            cls._instance.sock: Optional[socket.socket] = None
            cls._instance.joined_channels: Set[str] = set()
            cls._instance._last_ping = 0
            cls._instance._ping_task = None
            cls._instance._reconnect_task = None
        return cls._instance

    async def _keep_alive(self):
        while self._connected and self.sock:
            try:
                current_time = asyncio.get_event_loop().time()
                if current_time - self._last_ping >= 60:
                    self.sock.send("PING :tmi.twitch.tv\r\n".encode("utf-8"))
                    self._last_ping = current_time

                self.sock.settimeout(0.1)
                try:
                    response = self.sock.recv(2048).decode("utf-8")
                    if response.startswith("PING"):
                        pong = f"PONG {response.split('PING ')[1]}"
                        self.sock.send(f"{pong}\r\n".encode("utf-8"))
                    elif not response:
                        self._connected = False
                        break
                except socket.timeout:
                    pass
                except Exception:
                    self._connected = False
                    break

                await asyncio.sleep(1)
            except Exception:
                self._connected = False
                break

        await self._handle_disconnection()

    async def _handle_disconnection(self):
        if not self._connected:
            self.disconnect()

            if self._current_username and self._current_oauth:
                retry_count = 0
                max_retries = 5
                retry_delay = 5

                while retry_count < max_retries:
                    if await self.connect(self._current_username, self._current_oauth):
                        channels_to_rejoin = self.joined_channels.copy()
                        for channel in channels_to_rejoin:
                            await self._join_channel(channel)
                        return True

                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

                return False

    async def _join_channel(self, channel: str) -> bool:
        if not channel.startswith("#"):
            channel = f"#{channel}"

        try:
            join_command = f"JOIN {channel}\r\n"
            self.sock.send(join_command.encode("utf-8"))

            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 5:
                self.sock.settimeout(0.5)
                try:
                    response = self.sock.recv(2048).decode("utf-8")
                    if "PING" in response:
                        pong = f"PONG {response.split('PING :')[1]}"
                        self.sock.send(pong.encode("utf-8"))
                        continue

                    if f"JOIN {channel}" in response:
                        self.joined_channels.add(channel)
                        return True
                except socket.timeout:
                    continue
                except Exception:
                    return False

                await asyncio.sleep(0.1)

            return False

        except Exception:
            return False

    async def ensure_connected(self, username: str, oauth: str) -> bool:
        try:
            if (
                not self._connected
                or not self.sock
                or username != self._current_username
                or oauth != self._current_oauth
            ):
                if not await self.connect(username, oauth):
                    from utils.error_handler import handle_chat_connection_error

                    handle_chat_connection_error(None)
                    return False
            return True
        except Exception:
            from utils.error_handler import handle_chat_connection_error

            handle_chat_connection_error(None)
            return False

    async def connect(self, username: str, oauth: str) -> bool:
        try:
            if self._connected:
                self.disconnect()

            self.sock = socket.socket()
            self.sock.settimeout(10)
            self.sock.connect((self.server, self.port))

            self.sock.send(f"PASS {oauth}\r\n".encode("utf-8"))
            self.sock.send(f"NICK {username}\r\n".encode("utf-8"))
            self.sock.send(
                "CAP REQ :twitch.tv/commands twitch.tv/tags\r\n".encode("utf-8")
            )

            response = self.sock.recv(2048).decode("utf-8")

            if "Login authentication failed" in response:
                from utils.error_handler import handle_invalid_oauth

                handle_invalid_oauth(None)
                return False

            if ":tmi.twitch.tv 001" not in response:
                return False

            self._connected = True
            self._current_username = username
            self._current_oauth = oauth
            self.joined_channels.clear()

            if self._ping_task:
                self._ping_task.cancel()
            self._ping_task = asyncio.create_task(self._keep_alive())

            return True

        except Exception:
            self._connected = False
            self._current_username = None
            self._current_oauth = None
            return False

    def disconnect(self):
        try:
            if self._ping_task:
                self._ping_task.cancel()
                self._ping_task = None

            if self.sock:
                self.sock.close()

            self._connected = False
            self._current_username = None
            self._current_oauth = None
            self.joined_channels.clear()
            self.sock = None
        except Exception:
            pass

    async def send_message(self, channel: str, message: str) -> bool:
        try:
            if not await self.ensure_connected(
                self._current_username, self._current_oauth
            ):
                return False

            if not channel.startswith("#"):
                channel = f"#{channel}"

            if channel not in self.joined_channels:
                if not await self._join_channel(channel):
                    return False

            command = f"PRIVMSG {channel} :{message}\r\n"
            self.sock.send(command.encode("utf-8"))
            return True

        except Exception:
            self._connected = False
            return False
