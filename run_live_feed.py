"""Run the local Angel One feed and persist live 1m/5m candles.

Run after `python auth.py`:
    python run_live_feed.py
Stop with Ctrl+C. No order APIs are called.
"""
import sys
from src.iadew.angelone_client import cash_instrument, front_index_future, load_instruments
from src.iadew.angelone_stream import start_stream
from src.iadew.candle_aggregator import TickCandleAggregator
from src.iadew.config import settings


def main():
    if not settings.angel_jwt_token or not settings.angel_feed_token:
        raise SystemExit("Session tokens missing. Run: python auth.py")
    master = load_instruments()
    subscriptions = []
    for symbol in settings.watchlist:
        row = cash_instrument(master, symbol)
        if row is not None:
            subscriptions.append(("NSE", str(row["token"]), symbol))
        else:
            print(f"WARNING: NSE cash instrument not found: {symbol}")
    for name in ("NIFTY", "BANKNIFTY"):
        row = front_index_future(master, name)
        if row is not None:
            subscriptions.append(("NFO", str(row["token"]), str(row["symbol"])))
        else:
            print(f"WARNING: front-month future not found: {name}")
    if not subscriptions:
        raise SystemExit("No instruments resolved; cannot start feed.")

    aggregator = TickCandleAggregator(settings.db_path)
    print(f"Resolved {len(subscriptions)} instruments. Writing 1m/5m bars to {settings.db_path}")
    for exchange, token, label in subscriptions:
        print(f"  {exchange} {label} token={token}")
    print("Starting quote feed. No orders will be placed. Ctrl+C to stop.")
    try:
        start_stream(
            [(exchange, token) for exchange, token, _ in subscriptions],
            aggregator.on_tick,
            mode=2,
        )
    except KeyboardInterrupt:
        print("Stopping feed and flushing forming candles...")
    finally:
        aggregator.flush()
        print("Live candles saved.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Live feed error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
