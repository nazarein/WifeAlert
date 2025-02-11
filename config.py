class Config:
    PUBSUB_HOST = "wss://pubsub-edge.twitch.tv/v1"
    GQL_ENDPOINT = "https://gql.twitch.tv/gql"
    PING_INTERVAL = 180
    PING_TIMEOUT = 30
    RECONNECT_INTERVAL = 3
    NONCE_LENGTH = 30
    REQUEST_TIMEOUT = 30
    MAX_RETRY_COUNT = 1
    CLIENT_ID = "x0dee112urnxfxas4q9uto5m0a3p03"  # Public client ID
