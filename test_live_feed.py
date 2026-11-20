"""Local Angel One SmartAPI WebSocket V2 smoke test.

Run from the repository root after `python auth.py`:
    python test_live_feed.py

This subscribes to the configured NSE cash watchlist plus front-month NIFTY
and BANKNIFTY futures. It only receives/prints market data; it never places
orders. Press Ctrl+C to stop.
"""
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from src.iadew.angelone_client import (
    cash_instrument,
    front_index_future,
    load_instruments,
    make_smart_api,
)
from src.iadew.angelone_stream import start_stream
from src.iadew.config import settings

IST = ZoneInfo("Asia/Kolkata")


def resolve_subscriptions():
    master = load_instruments()
    subscriptions = []
    unresolved = []

    for symbol in settings.watchlist:
        row = cash_instrument(master, symbol)
        if row is None:
            unresolved.append(f"NSE:{symbol}")
        else:
            subscriptions.append(("NSE", str(row["token"]), f"{symbol} (NSE cash)"))

    for index_name in ("NIFTY", "BANKNIFTY"):
        row = front_index_future(master, index_name)
        if row is None:
            unresolved.append(f"NFO:{index_name} front future")
        else:
            label = str(row.get("symbol") or index_name)
            subscriptions.append(("NFO", str(row["token"]), label))

    return subscriptions, unresolved


def print_tick(message):
    stamp = datetime.now(IST).strftime("%H:%M:%S")
    if isinstance(message, dict):
        # SmartAPI packet keys vary by subscription mode/SDK version.
        useful = {
            key: message.get(key)
            for key in (
                "token", "symboltoken", "exchange_type", "exchangeType",
                "ltp", "last_traded_price", "last_traded_quantity",
                "volume_trade_for_the_day", "average_traded_price",
                "open", "high", "low", "close", "exchange_timestamp",
            )
            if message.get(key) is not None
        }
        payload = json.dumps(useful or message, default=str)
    else:
        payload = repr(message)
    print(f"[{stamp} IST] TICK {payload}", flush=True)


def main():
    if not settings.angel_jwt_token or not settings.angel_feed_token:
        raise SystemExit("Session tokens missing. Run: python auth.py")

    try:
        make_smart_api()  # Validate that local session configuration is present.
        subscriptions, unresolved = resolve_subscriptions()
    except Exception as exc:
        raise SystemExit(f"Pre-flight failed: {type(exc).__name__}: {exc}") from exc

    if unresolved:
        print("WARNING: Could not resolve: " + ", ".join(unresolved), flush=True)
    if not subscriptions:
        raise SystemExit("No instruments resolved; cannot subscribe.")

    print("IADEW Angel One live-feed smoke test", flush=True)
    print(f"Resolved {len(subscriptions)} instruments:", flush=True)
    for exchange, token, label in subscriptions:
        print(f"  {exchange} token={token}  {label}", flush=True)
    print("Connecting in Quote mode (2). Press Ctrl+C to stop.", flush=True)
    print("No orders will be placed by this script.", flush=True)

    try:
        # The adapter expects (exchange segment, token) pairs.
        start_stream(
            [(exchange, token) for exchange, token, _ in subscriptions],
            print_tick,
            mode=2,
        )
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
    except Exception as exc:
        print(f"Feed test failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
