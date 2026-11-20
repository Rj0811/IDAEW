"""Angel One SmartAPI WebSocket V2 adapter.

This module exposes decoded packets to a caller callback. It does not place,
modify or cancel orders. DEPTH mode is restricted by the official SDK to NSE
cash (exchange type 1), with a maximum of 50 subscribed tokens.
"""
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from .config import settings

EXCHANGE_TYPES = {"NSE": 1, "NFO": 2, "BSE": 3, "BFO": 4, "MCX": 5}
DEPTH_TOKEN_LIMIT = 50


def start_stream(subscriptions, on_tick, mode=2):
    """Start a SmartAPI V2 feed.

    Args:
        subscriptions: iterable of (exchange_segment, symbol_token).
        on_tick: callback receiving each SDK-decoded packet.
        mode: 1=LTP, 2=Quote, 3=Snap Quote, 4=DEPTH20 (NSE cash only).
    """
    required = (
        settings.angel_api_key,
        settings.angel_client_code,
        settings.angel_jwt_token,
        settings.angel_feed_token,
    )
    if not all(required):
        raise RuntimeError("Run python auth.py; Angel One JWT and feed tokens are required.")
    if mode not in (1, 2, 3, 4):
        raise ValueError("SmartAPI V2 mode must be 1 (LTP), 2 (Quote), 3 (Snap Quote) or 4 (Depth20).")

    grouped = {}
    for exchange, token in subscriptions:
        exchange_type = EXCHANGE_TYPES.get(exchange.upper())
        if exchange_type is None:
            raise ValueError(f"Unsupported Angel One exchange segment: {exchange}")
        if mode == 4 and exchange_type != 1:
            raise ValueError("SmartAPI Depth20 mode supports NSE cash only (exchange type 1) in the official SDK.")
        grouped.setdefault(exchange_type, []).append(str(token))

    if not grouped:
        raise ValueError("At least one instrument subscription is required.")
    if mode == 4 and sum(map(len, grouped.values())) > DEPTH_TOKEN_LIMIT:
        raise ValueError(f"Depth20 mode supports at most {DEPTH_TOKEN_LIMIT} tokens per subscription.")

    token_list = [
        {"exchangeType": exchange_type, "tokens": tokens}
        for exchange_type, tokens in grouped.items()
    ]
    socket = SmartWebSocketV2(
        settings.angel_jwt_token,
        settings.angel_api_key,
        settings.angel_client_code,
        settings.angel_feed_token,
        max_retry_attempt=3,
        retry_strategy=1,
        retry_delay=5,
        retry_duration=60,
    )
    socket.on_data = lambda wsapp, message: on_tick(message)
    socket.on_error = lambda wsapp, error: print(f"Angel One WebSocket error: {error}")
    socket.on_close = lambda wsapp: print("Angel One WebSocket closed")

    def on_open(wsapp):
        socket.subscribe("IADEW00001", mode, token_list)

    socket.on_open = on_open
    socket.connect()
    return socket
