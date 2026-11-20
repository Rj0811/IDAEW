"""Tick-to-candle aggregation for Angel One SmartAPI quote packets.

Angel One prices are in paise and are normalized to rupees. Day volume is
cumulative; each packet contributes only the increase since the prior packet.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


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
        # Persist the still-forming candle on every tick so the dashboard can
        # read it without waiting for the next interval or Ctrl+C.
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
                elif previous is not None and cumulative < previous:
                    # Day-volume reset or feed reset: establish a new baseline.
                    delta = 0
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
