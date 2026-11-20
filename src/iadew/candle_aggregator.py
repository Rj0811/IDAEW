"""Tick-to-candle and depth-snapshot persistence for Angel One packets."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class DepthSnapshotStore:
    """Persist each received Depth20 snapshot; snapshots are not order events."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10)

    def _init_db(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS depth_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL,
                    exchange_type INTEGER NOT NULL,
                    exchange_timestamp TEXT,
                    received_timestamp TEXT NOT NULL,
                    buy_levels_json TEXT NOT NULL,
                    sell_levels_json TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'angelone_websocket_depth20',
                    quality_flags TEXT NOT NULL DEFAULT ''
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_depth_snapshots_token_time ON depth_snapshots(token, received_timestamp DESC)")

    @staticmethod
    def _levels(packet, key):
        levels = packet.get(key) or []
        normalized = []
        for level in levels:
            try:
                price = float(level.get("price", 0)) / 100.0
                quantity = int(level.get("quantity", 0))
                orders = int(level.get("num_of_orders", 0))
                normalized.append({"price": price, "quantity": quantity, "orders": orders})
            except (TypeError, ValueError):
                continue
        return normalized

    def on_depth(self, packet):
        if not isinstance(packet, dict) or not packet.get("token"):
            return
        buys = self._levels(packet, "depth_20_buy_data")
        sells = self._levels(packet, "depth_20_sell_data")
        if not buys and not sells:
            return
        received = datetime.now(timezone.utc).astimezone(IST).isoformat()
        raw_ts = packet.get("exchange_timestamp") or packet.get("packet_received_time")
        try:
            exchange_ts = datetime.fromtimestamp(float(raw_ts) / 1000, tz=timezone.utc).astimezone(IST).isoformat() if raw_ts else None
        except (TypeError, ValueError, OverflowError):
            exchange_ts = None
        flags = []
        if len(buys) != 20 or len(sells) != 20:
            flags.append("incomplete_depth_levels")
        with self._connect() as con:
            con.execute("""
                INSERT INTO depth_snapshots
                (token, exchange_type, exchange_timestamp, received_timestamp,
                 buy_levels_json, sell_levels_json, quality_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(packet["token"]), int(packet.get("exchange_type", 0)),
                exchange_ts, received, json.dumps(buys), json.dumps(sells),
                ",".join(flags),
            ))


class TickCandleAggregator:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.current = {}
        self.last_cum_volume = {}
        self._init_db()

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=10)

    def _init_db(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS live_bars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL,
                    exchange_type INTEGER,
                    timeframe TEXT NOT NULL,
                    bar_time TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL DEFAULT 0,
                    tick_count INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL DEFAULT 'angelone_websocket',
                    UNIQUE(token, timeframe, bar_time)
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_live_bars_time ON live_bars(bar_time DESC)")

    @staticmethod
    def _bucket(ts, minutes):
        minute = (ts.minute // minutes) * minutes
        return ts.replace(minute=minute, second=0, microsecond=0)

    def _save(self, key, candle):
        token, timeframe, bucket = key
        with self._connect() as con:
            con.execute("""
                INSERT INTO live_bars
                (token, exchange_type, timeframe, bar_time, open, high, low, close, volume, tick_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token, timeframe, bar_time) DO UPDATE SET
                  high=excluded.high, low=excluded.low, close=excluded.close,
                  volume=excluded.volume, tick_count=excluded.tick_count
            """, (
                token, candle["exchange_type"], timeframe, bucket.isoformat(),
                candle["open"], candle["high"], candle["low"], candle["close"],
                candle["volume"], candle["tick_count"],
            ))

    def _apply(self, token, exchange_type, timeframe, bucket, price, volume_delta):
        key = (token, timeframe, bucket)
        candle = self.current.get(key)
        if candle is None:
            candle = {
                "exchange_type": exchange_type, "open": price, "high": price,
                "low": price, "close": price, "volume": 0, "tick_count": 0,
            }
            self.current[key] = candle
        candle["high"] = max(candle["high"], price)
        candle["low"] = min(candle["low"], price)
        candle["close"] = price
        candle["volume"] += max(0, int(volume_delta))
        candle["tick_count"] += 1
        self._save(key, candle)

    def on_tick(self, packet):
        if not isinstance(packet, dict):
            return
        token = str(packet.get("token") or packet.get("symboltoken") or "")
        raw_price = packet.get("last_traded_price")
        if not token or raw_price is None:
            return
        try:
            price = float(raw_price) / 100.0
            if price <= 0:
                return
            raw_ts = packet.get("exchange_timestamp")
            ts = (datetime.fromtimestamp(float(raw_ts) / 1000, tz=timezone.utc)
                  if raw_ts else datetime.now(timezone.utc)).astimezone(IST)
            cumulative = packet.get("volume_trade_for_the_day")
            delta = 0
            if cumulative is not None:
                cumulative = int(cumulative)
                previous = self.last_cum_volume.get(token)
                if previous is not None and cumulative >= previous:
                    delta = cumulative - previous
                self.last_cum_volume[token] = cumulative
            for timeframe, minutes in (("1m", 1), ("5m", 5)):
                bucket = self._bucket(ts, minutes)
                for key in list(self.current):
                    old_token, old_tf, old_bucket = key
                    if old_token == token and old_tf == timeframe and old_bucket < bucket:
                        self._save(key, self.current.pop(key))
                self._apply(token, packet.get("exchange_type"), timeframe, bucket, price, delta)
        except (TypeError, ValueError, OverflowError):
            return

    def flush(self):
        for key, candle in list(self.current.items()):
            self._save(key, candle)
