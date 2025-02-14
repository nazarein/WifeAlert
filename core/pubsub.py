"""
Twitch PubSub message handling and topic management. Provides data structures
for managing WebSocket subscriptions and message formatting for the Twitch
PubSub system. Used for real-time stream status notifications.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import secrets
import json
import websockets
import asyncio
from config import Config


@dataclass
class Topic:
    """
    Represents a Twitch PubSub topic subscription.
    Combines event type (e.g., 'video-playback-by-id') with target ID
    to form a complete topic identifier for the PubSub system.

    Attributes:
        event_type: Type of event to subscribe to
        target_id: Channel or resource ID to monitor
    """

    event_type: str
    target_id: str

    @property
    def id(self) -> str:
        """
        Generates the complete topic identifier by combining event type and target.

        Returns:
            Formatted topic string (e.g., 'video-playback-by-id.1234567')
        """
        return f"{self.event_type}.{self.target_id}"


class PubSubRequest:
    """
    Formats subscription/unsubscription requests for Twitch PubSub.
    Handles message formatting with secure nonce generation for
    request tracking and verification.

    Attributes:
        topics: List of topics to subscribe/unsubscribe
        nonce: Unique identifier for request tracking
        subscribe: True for subscribe, False for unsubscribe
    """

    def __init__(self, topics: List[Topic], subscribe: bool):
        self.topics = topics
        self.nonce = secrets.token_urlsafe(Config.NONCE_LENGTH)
        self.subscribe = subscribe

    def get_payload(self) -> dict:
        """
        Creates the formatted message payload for PubSub WebSocket.

        Returns:
            Dict containing properly formatted request for Twitch PubSub:
            {
                "type": "LISTEN"/"UNLISTEN",
                "nonce": "random_string",
                "data": {"topics": ["topic1", "topic2"]}
            }
        """
        return {
            "type": "LISTEN" if self.subscribe else "UNLISTEN",
            "nonce": self.nonce,
            "data": {"topics": [topic.id for topic in self.topics]},
        }
