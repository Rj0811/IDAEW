"""Angel One SmartAPI WebSocket V2 adapter.

This module exposes decoded quote packets to a caller callback. It does not
place, modify or cancel orders.
"""
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from .config import settings

EXCHANGE_TYPES = {"NSE": 1, "NFO": 2, "BSE": 3, "BFO": 4, "MCX": 5}

def start_stream(subscriptions, on_tick, mode=2):
    """Start a SmartAPI V2 feed.

    Args:
        subscriptions: iterable of (exchange_segment, symbol_token), e.g.
            [("NSE", "3045"), ("NFO", "123456")].
        on_tick: callback receiving each SDK-decoded tick packet.
        mode: 1=LTP, 2=Quote, 3=Snap Quote. Start with Quote mode for MVP.
    """
    required = (
        settings.angel_api_key,
        settings.angel_client_code,
        settings.angel_jwt_token,
        settings.angel_feed_token,
    )
    if not all(required):
        raise RuntimeError("Run python auth.py; Angel One JWT and feed tokens are required.")
    if mode not in (1, 2, 3):
        raise ValueError("SmartAPI V2 mode must be 1 (LTP), 2 (Quote) or 3 (Snap Quote).")

    grouped = {}
    for exchange, token in subscriptions:
        exchange_type = EXCHANGE_TYPES.get(exchange.upper())
        if exchange_type is None:
            raise ValueError(f"Unsupported Angel One exchange segment: {exchange}")
        grouped.setdefault(exchange_type, []).append(str(token))

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
