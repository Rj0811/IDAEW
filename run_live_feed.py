"""Run Angel One quote/candle collection or combined NSE Depth20 + quote collection."""
import argparse
import sys
from src.iadew.angelone_client import cash_instrument, front_index_future, load_instruments
from src.iadew.angelone_stream import start_stream
from src.iadew.candle_aggregator import DepthSnapshotStore, TickCandleAggregator
from src.iadew.config import settings


def main():
    parser = argparse.ArgumentParser(description="IADEW Angel One market-data collector")
    parser.add_argument("--depth", action="store_true",
                        help="Collect NSE cash Depth20 and matching Quote candles on one WebSocket")
    args = parser.parse_args()
    if not settings.angel_jwt_token or not settings.angel_feed_token:
        raise SystemExit("Session tokens missing. Run: python auth.py")

    master = load_instruments()
    cash = []
    for symbol in settings.watchlist:
        row = cash_instrument(master, symbol)
        if row is not None:
            cash.append(("NSE", str(row["token"]), symbol))
        else:
            print(f"WARNING: NSE cash instrument not found: {symbol}")

    futures = []
    for name in ("NIFTY", "BANKNIFTY"):
        row = front_index_future(master, name)
        if row is not None:
            futures.append(("NFO", str(row["token"]), str(row["symbol"])))
        else:
            print(f"WARNING: front-month future not found: {name}")

    if not cash:
        raise SystemExit("No NSE cash instruments resolved; cannot start feed.")

    if args.depth:
        if len(cash) > 50:
            raise SystemExit(f"Depth20 supports at most 50 tokens; watchlist resolved {len(cash)}.")
        depth_store = DepthSnapshotStore(settings.db_path)
        candle_store = TickCandleAggregator(settings.db_path)
        def callback(packet):
            if isinstance(packet, dict) and "depth_20_buy_data" in packet:
                depth_store.on_depth(packet)
            elif isinstance(packet, dict) and packet.get("subscription_mode") == 2:
                candle_store.on_tick(packet)
        quote_subs = [(ex, token) for ex, token, _ in cash + futures]
        depth_subs = [(ex, token) for ex, token, _ in cash]
        print(f"Depth20: {len(depth_subs)} NSE cash tokens. Quote candles: {len(quote_subs)} cash/futures tokens.")
        print("Depth and quote modes share one WebSocket session for time-aligned validation.")
        try:
            start_stream(depth_subs, callback, mode=4, quote_subscriptions=quote_subs)
        except KeyboardInterrupt:
            print("Stopping combined depth + quote collector...")
        finally:
            candle_store.flush()
    else:
        subscriptions = cash + futures
        candle_store = TickCandleAggregator(settings.db_path)
        print(f"Resolved {len(subscriptions)} instruments. Writing 1m/5m bars to {settings.db_path}")
        try:
            start_stream([(ex, token) for ex, token, _ in subscriptions],
                         candle_store.on_tick, mode=2)
        except KeyboardInterrupt:
            print("Stopping quote collector...")
        finally:
            candle_store.flush()

    print("Collector stopped. No orders were placed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Live feed error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
