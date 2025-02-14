"""
Application configuration constants. Defines connection endpoints,
timeouts, and other operational parameters for Twitch API interaction
and WebSocket connections.
"""


class Config:
    """
    Static configuration values for application behavior.
    Contains endpoints, timing parameters, and API credentials.
    All values are read-only and used across the application.
    """

    # Twitch API endpoints
    PUBSUB_HOST = (
        "wss://pubsub-edge.twitch.tv/v1"  # WebSocket endpoint for stream events
    )
    GQL_ENDPOINT = "https://gql.twitch.tv/gql"  # GraphQL API endpoint for queries

    # Connection timing parameters (in seconds)
    PING_INTERVAL = 180  # Time between keepalive pings
    PING_TIMEOUT = 30  # Time to wait for pong response
    RECONNECT_INTERVAL = 3  # Initial delay before reconnection attempt
    REQUEST_TIMEOUT = 30  # Timeout for API requests

    # Security and retry settings
    NONCE_LENGTH = 30  # Length of random nonce for PubSub messages
    MAX_RETRY_COUNT = 1  # Number of retry attempts for operations

    # API credentials
    CLIENT_ID = (
        "kimne78kx3ncx6brgo4mv6wki5h1ko"  # Public Twitch client ID(hidden endpoint)
    )
