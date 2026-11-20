"""Run the Angel One live collector.

Quote/candle mode (existing): python run_live_feed.py
NSE cash Depth20 mode:       python run_live_feed.py --depth
Depth mode is a separate run and supports NSE cash only, max 50 tokens.
No order APIs are called.
"""
import argparse
import sys
from src.iadew.angelone_client import cash_instrument, front_index_future, load_instruments
from src.iadew.angelone_stream import start_stream
from src.iadew.candle_aggregator import DepthSnapshotStore, TickCandleAggregator
from src.iadew.config import settings


def main():
    parser = argparse.ArgumentParser(description="IADEW Angel One market-data collector")
    parser.add_argument("--depth", action="store_true", help="Collect NSE cash Depth20 snapshots instead of quote candles")
    args = parser.parse_args()

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

    if not args.depth:
        for name in ("NIFTY", "BANKNIFTY"):
            row = front_index_future(master, name)
            if row is not None:
                subscriptions.append(("NFO", str(row["token"]), str(row["symbol"])))
            else:
                print(f"WARNING: front-month future not found: {name}")

    if not subscriptions:
        raise SystemExit("No instruments resolved; cannot start feed.")
    if args.depth and len(subscriptions) > 50:
        raise SystemExit(f"Depth20 supports at most 50 tokens; watchlist resolved {len(subscriptions)}. Reduce watchlist first.")

    if args.depth:
        collector = DepthSnapshotStore(settings.db_path)
        print(f"Resolved {len(subscriptions)} NSE cash instruments. Persisting Depth20 snapshots to {settings.db_path}")
        callback = collector.on_depth
        mode = 4
        print("Starting NSE cash Depth20 feed. Snapshots are not order-by-order events. Ctrl+C to stop.")
    else:
        collector = TickCandleAggregator(settings.db_path)
        print(f"Resolved {len(subscriptions)} instruments. Writing 1m/5m bars to {settings.db_path}")
        callback = collector.on_tick
        mode = 2
        print("Starting quote feed. No orders will be placed. Ctrl+C to stop.")

    for exchange, token, label in subscriptions:
        print(f"  {exchange} {label} token={token}")
    try:
        start_stream([(exchange, token) for exchange, token, _ in subscriptions], callback, mode=mode)
    except KeyboardInterrupt:
        print("Stopping feed...")
    finally:
        if isinstance(collector, TickCandleAggregator):
            collector.flush()
        print("Collector stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Live feed error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
