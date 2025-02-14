"""
Base monitor class for Twitch stream status tracking. Handles WebSocket connections
to Twitch's PubSub system, manages channel subscriptions, and processes stream
up/down events. Provides core functionality for real-time stream monitoring.
"""

import asyncio
import json
import websockets
import aiohttp
from typing import Set, List, Dict
from config import Config
from core.gql_client import GQLClient
from core.pubsub import Topic, PubSubRequest
from utils.error_handler import handle_pubsub_connection_error


class TwitchMonitor:
    """
    Core monitor for tracking Twitch stream status changes. Features:
    - WebSocket connection to Twitch PubSub
    - Channel ID lookup and management
    - Automatic reconnection handling
    - Connection health monitoring
    - Event handling for stream status changes
    """

    def __init__(self, client_id: str, usernames: List[str]):
        self.client_id = client_id
        self.usernames = [username.lower() for username in usernames]
        self.channel_ids = []
        self.username_to_id = {}
        self.live_channels: Set[str] = set()
        self.ws = None
        self.should_run = True
        self.gql_client = GQLClient(client_id)
        self.subscribed_topics: List[Topic] = []
        self.pending_requests: Dict[str, PubSubRequest] = {}
        self.notification_manager = None
        self.last_pong = 0
        self._running_task = None

    async def initialize(self):
        """
        Sets up initial monitor state by looking up channel IDs for usernames.
        Updates internal mappings and prepares channel list for monitoring.
        Handles missing or invalid usernames gracefully.
        """
        try:
            usernames_to_lookup = [
                username
                for username in self.usernames
                if username not in self.username_to_id
            ]
            if usernames_to_lookup:
                new_ids = await self.gql_client.lookup_usernames(usernames_to_lookup)
                self.username_to_id.update(new_ids)
            self.channel_ids = []
            missing_usernames = []
            for username in self.usernames:
                if username in self.username_to_id:
                    self.channel_ids.append(self.username_to_id[username])
                else:
                    missing_usernames.append(username)
        except Exception:
            pass

    async def handle_message(self, message_data: dict):
        """
        Processes incoming WebSocket messages from Twitch PubSub.
        Handles different message types:
        - PONG: Connection health checks
        - RESPONSE: Subscription confirmations
        - MESSAGE: Stream status change events

        Args:
            message_data: Raw message data from WebSocket
        """
        try:
            msg_type = message_data.get("type")
            if msg_type == "PONG":
                self.last_pong = asyncio.get_event_loop().time()
                return
            if msg_type == "RESPONSE":
                nonce = message_data.get("nonce")
                if nonce in self.pending_requests:
                    self.pending_requests.pop(nonce)
                return
            if msg_type == "MESSAGE":
                data = json.loads(message_data["data"]["message"])
                topic = message_data["data"]["topic"]
                event_type = data.get("type", "unknown")
                if event_type not in ["stream-up", "stream-down"]:
                    return
                channel_id = topic.split(".")[-1]

                if event_type == "stream-up":
                    if channel_id in self.live_channels:
                        return

                username = next(
                    (
                        name
                        for name, id_ in self.username_to_id.items()
                        if id_ == channel_id
                    ),
                    channel_id,
                )
                if event_type == "stream-up":
                    await self.handle_stream_up(channel_id, data.get("server_time"))
                elif event_type == "stream-down":
                    await self.handle_stream_down(channel_id)
        except Exception:
            pass

    async def maintain_connection(self, websocket):
        """
        Maintains WebSocket connection health through ping/pong mechanism.
        Monitors connection timeouts and triggers reconnection if needed.
        Runs continuously while monitor is active.
        """
        last_pong = asyncio.get_event_loop().time()
        while self.should_run:
            try:
                current_time = asyncio.get_event_loop().time()
                if current_time - last_pong > Config.PING_TIMEOUT:
                    break

                if hasattr(websocket, "last_recv_time"):
                    if (
                        current_time - websocket.last_recv_time
                        > Config.PING_TIMEOUT * 3
                    ):
                        break

                await websocket.send(json.dumps({"type": "PING"}))
                await asyncio.sleep(Config.PING_INTERVAL)

            except Exception:
                break

    async def subscribe_to_topics(self, websocket):
        """
        Subscribes to PubSub topics for monitored channels.
        Implements retry logic for failed subscriptions.
        Verifies subscription responses and handles errors.
        """
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                topics = [
                    Topic("video-playback-by-id", channel_id)
                    for channel_id in self.channel_ids
                ]

                if not topics:
                    return

                request = PubSubRequest(topics, True)
                self.pending_requests[request.nonce] = request

                await websocket.send(json.dumps(request.get_payload()))

                message = await asyncio.wait_for(
                    websocket.recv(), timeout=Config.REQUEST_TIMEOUT
                )
                response = json.loads(message)

                if response.get("type") == "RESPONSE":
                    if response.get("error"):
                        raise Exception(f"Subscription error: {response['error']}")
                    else:
                        return

            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise

    async def listen_for_stream_status(self):
        """
        Main WebSocket listener loop. Handles:
        - Connection establishment and maintenance
        - Message processing
        - Error recovery and reconnection
        - Connection health monitoring
        Implements exponential backoff for reconnection attempts.
        """
        reconnect_delay = Config.RECONNECT_INTERVAL
        max_reconnect_delay = 60
        connection_attempts = 0
        max_attempts = 3

        while self.should_run:
            try:
                async with websockets.connect(
                    Config.PUBSUB_HOST,
                    ping_interval=None,
                    close_timeout=Config.PING_TIMEOUT,
                    max_size=None,
                ) as websocket:
                    connection_attempts = 0
                    self.ws = websocket
                    reconnect_delay = Config.RECONNECT_INTERVAL

                    try:
                        await self.subscribe_to_topics(websocket)
                    except asyncio.CancelledError:
                        break

                    maintenance_task = asyncio.create_task(
                        self.maintain_connection(websocket)
                    )

                    try:
                        while self.should_run:
                            try:
                                message = await asyncio.wait_for(
                                    websocket.recv(), timeout=Config.PING_TIMEOUT * 2
                                )
                                await self.handle_message(json.loads(message))
                            except (asyncio.TimeoutError, websockets.ConnectionClosed):
                                break
                            except asyncio.CancelledError:
                                break
                    finally:
                        maintenance_task.cancel()
                        try:
                            await maintenance_task
                        except asyncio.CancelledError:
                            pass

                if not self.should_run:
                    break

                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

            except asyncio.CancelledError:
                break
            except Exception:
                connection_attempts += 1
                if connection_attempts >= max_attempts:
                    if (
                        hasattr(self, "notification_manager")
                        and self.notification_manager
                    ):
                        handle_pubsub_connection_error(self.notification_manager.window)
                    connection_attempts = 0
                if not self.should_run:
                    break
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    async def resubscribe_all(self):
        if self.ws and self.ws.open:
            await self.subscribe_to_topics(self.ws)

    async def reconnect(self):
        """
        Performs clean reconnection of the monitor.
        - Closes existing connection
        - Clears internal state
        - Reinitializes channel subscriptions
        - Establishes new WebSocket connection
        Maintains monitor instance for continuity.
        """
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

        self.subscribed_topics.clear()
        self.pending_requests.clear()
        self.should_run = True

        await self.initialize()

        if hasattr(self, "_running_task") and self._running_task:
            if not self._running_task.done():
                self._running_task.cancel()
            self._running_task = None

        await self.listen_for_stream_status()

    async def run(self):
        """
        Main entry point for monitor operation.
        Initializes monitoring state and starts WebSocket listener.
        Handles graceful shutdown on cancellation.
        Manages monitor lifecycle and cleanup.
        """
        if (
            hasattr(self, "_running_task")
            and self._running_task
            and not self._running_task.done()
        ):
            return

        try:
            await self.initialize()
            await self.listen_for_stream_status()
        except asyncio.CancelledError:
            self.should_run = False
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
            return
        except Exception:
            pass
        finally:
            self.should_run = False
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass

    async def handle_stream_up(self, channel_id: str, server_time: str):
        """
        Virtual method for handling stream start events.
        Implemented by subclasses to define specific behavior.

        Args:
            channel_id: Twitch channel ID that went live
            server_time: Server timestamp of the event
        """
        pass

    async def handle_stream_down(self, channel_id: str):
        """
        Handles stream end events by updating internal state.
        Updates live channel tracking and UI indicators.

        Args:
            channel_id: Twitch channel ID that went offline
        """
        if channel_id in self.live_channels:
            self.live_channels.remove(channel_id)
            self.update_live_indicators()

    def update_live_indicators(self):
        """
        Virtual method for updating UI elements with live status.
        Implemented by subclasses to handle specific UI updates.
        """
        pass
