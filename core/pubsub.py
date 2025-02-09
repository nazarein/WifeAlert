from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import secrets
import json
import websockets
import asyncio
from config import Config


@dataclass
class Topic:
    event_type: str
    target_id: str

    @property
    def id(self) -> str:
        return f"{self.event_type}.{self.target_id}"


class PubSubRequest:
    def __init__(self, topics: List[Topic], subscribe: bool):
        self.topics = topics
        self.nonce = secrets.token_urlsafe(Config.NONCE_LENGTH)
        self.subscribe = subscribe

    def get_payload(self) -> dict:
        return {
            "type": "LISTEN" if self.subscribe else "UNLISTEN",
            "nonce": self.nonce,
            "data": {"topics": [topic.id for topic in self.topics]},
        }
