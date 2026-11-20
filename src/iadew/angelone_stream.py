"""Angel One SmartAPI WebSocket V2 adapter with optional dual-mode collection."""
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from .config import settings

EXCHANGE_TYPES = {"NSE": 1, "NFO": 2, "BSE": 3, "BFO": 4, "MCX": 5}
DEPTH_TOKEN_LIMIT = 50


def _group_subscriptions(subscriptions, depth=False):
    grouped = {}
    for exchange, token in subscriptions:
        exchange_type = EXCHANGE_TYPES.get(exchange.upper())
        if exchange_type is None:
            raise ValueError(f"Unsupported Angel One exchange segment: {exchange}")
        if depth and exchange_type != 1:
            raise ValueError("SmartAPI Depth20 mode supports NSE cash only (exchange type 1) in the official SDK.")
        grouped.setdefault(exchange_type, []).append(str(token))
    return [{"exchangeType": key, "tokens": value} for key, value in grouped.items()]


def start_stream(subscriptions, on_tick, mode=2, quote_subscriptions=None):
    """Start one socket; optionally subscribe to Quote mode alongside Depth20."""
    required = (settings.angel_api_key, settings.angel_client_code,
                settings.angel_jwt_token, settings.angel_feed_token)
    if not all(required):
        raise RuntimeError("Run python auth.py; Angel One JWT and feed tokens are required.")
    if mode not in (1, 2, 3, 4):
        raise ValueError("SmartAPI V2 mode must be 1, 2, 3 or 4.")
    token_list = _group_subscriptions(subscriptions, depth=(mode == 4))
    if not token_list:
        raise ValueError("At least one instrument subscription is required.")
    if mode == 4 and sum(len(x["tokens"]) for x in token_list) > DEPTH_TOKEN_LIMIT:
        raise ValueError(f"Depth20 mode supports at most {DEPTH_TOKEN_LIMIT} tokens.")
    quote_list = _group_subscriptions(quote_subscriptions or []) if quote_subscriptions else []

    socket = SmartWebSocketV2(
        settings.angel_jwt_token, settings.angel_api_key,
        settings.angel_client_code, settings.angel_feed_token,
        max_retry_attempt=3, retry_strategy=1, retry_delay=5, retry_duration=60,
    )
    socket.on_data = lambda wsapp, message: on_tick(message)
    socket.on_error = lambda wsapp, error: print(f"Angel One WebSocket error: {error}")
    socket.on_close = lambda wsapp: print("Angel One WebSocket closed")

    def on_open(wsapp):
        socket.subscribe("IADEWDEPTH1", mode, token_list)
        if quote_list:
            socket.subscribe("IADEWQUOTE1", 2, quote_list)

    socket.on_open = on_open
    socket.connect()
    return socket
