"""Historical 5-minute replay and deterministic paper backtest.

Signals are evaluated only after a bar closes and filled at the next bar open.
OHLCV-only strategies; no footprint/CVD/absorption claims. If stop and target
are both touched in one bar, the conservative stop-first assumption is used.
"""
from __future__ import annotations

import math
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .angelone_client import load_instruments, make_smart_api, cash_instrument, front_index_future
from .config import settings

IST = ZoneInfo("Asia/Kolkata")
EXCHANGE_BY_TYPE = {1: "NSE", 2: "NFO"}


def trading_days_to_calendar_days(trading_days: int) -> int:
    return int(math.ceil(trading_days * 7 / 5)) + 14


def fetch_history_days(api, token: str, exchange: str, calendar_days: int,
                       interval: str = "FIVE_MINUTE", pause_seconds: float = 0.45) -> pd.DataFrame:
    """Fetch history in <=90-calendar-day windows (SmartAPI 5m limit is 100 days)."""
    end = datetime.now()
    start = end - timedelta(days=calendar_days)
    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=90), end)
        params = {
            "exchange": exchange,
            "symboltoken": str(token),
            "interval": interval,
            "fromdate": cursor.strftime("%Y-%m-%d %H:%M"),
            "todate": chunk_end.strftime("%Y-%m-%d %H:%M"),
        }
        response = api.getCandleData(params)
        if not response or response.get("status") is not True:
            msg = (response or {}).get("message", "No response")
            code = (response or {}).get("errorcode", "")
            raise RuntimeError(f"Historical API {exchange}:{token} {code}: {msg}")
        rows = response.get("data") or []
        if rows:
            part = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            part["date"] = pd.to_datetime(part["date"], utc=True).dt.tz_convert(IST)
            for col in ["open", "high", "low", "close", "volume"]:
                part[col] = pd.to_numeric(part[col], errors="coerce")
            chunks.append(part.dropna())
        cursor = chunk_end
        if cursor < end:
            time.sleep(pause_seconds)
    if not chunks:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    result = pd.concat(chunks, ignore_index=True)
    return (result.drop_duplicates("date").sort_values("date")
            .reset_index(drop=True))


def prepare_bars(frame: pd.DataFrame) -> pd.DataFrame:
    x = frame.copy().sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if x.empty:
        return x
    x["session"] = x["date"].dt.tz_convert(IST).dt.strftime("%Y-%m-%d")
    x["ema9"] = x["close"].ewm(span=9, adjust=False).mean()
    x["ema20"] = x["close"].ewm(span=20, adjust=False).mean()
    prev_close = x["close"].shift(1)
    tr = pd.concat([
        x["high"] - x["low"],
        (x["high"] - prev_close).abs(),
        (x["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    x["atr14"] = tr.rolling(14, min_periods=14).mean()
    typical = (x["high"] + x["low"] + x["close"]) / 3
    cum_pv = (typical * x["volume"]).groupby(x["session"]).cumsum()
    cum_vol = x["volume"].groupby(x["session"]).cumsum().replace(0, np.nan)
    x["vwap"] = cum_pv / cum_vol
    x["prior_high20"] = x["high"].shift(1).rolling(20, min_periods=20).max()
    x["prior_low20"] = x["low"].shift(1).rolling(20, min_periods=20).min()
    return x


def build_signals(frame: pd.DataFrame, style: str) -> pd.Series:
    x = frame
    if style == "intraday":
        cross_up = (x["close"].shift(1) <= x["ema9"].shift(1)) & (x["close"] > x["ema9"])
        cross_dn = (x["close"].shift(1) >= x["ema9"].shift(1)) & (x["close"] < x["ema9"])
        long_ok = cross_up & (x["ema9"] > x["ema20"]) & (x["close"] > x["vwap"])
        short_ok = cross_dn & (x["ema9"] < x["ema20"]) & (x["close"] < x["vwap"])
    elif style == "swing":
        long_ok = (x["close"] > x["prior_high20"]) & (x["ema9"] > x["ema20"])
        short_ok = (x["close"] < x["prior_low20"]) & (x["ema9"] < x["ema20"])
    else:
        raise ValueError("style must be intraday or swing")
    return pd.Series(np.select([long_ok, short_ok], [1, -1], default=0), index=x.index)


def simulate_instrument(frame: pd.DataFrame, symbol: str, segment: str, style: str,
                        capital: float = 500_000, risk_pct: float = 0.005,
                        stop_atr: float = 1.5, reward_risk: float = 2.0,
                        cost_bps_per_side: float = 3.0, slippage_bps: float = 1.0,
                        max_hold_bars: int | None = None) -> list[dict]:
    x = prepare_bars(frame)
    if len(x) < 40:
        return []
    x["signal"] = build_signals(x, style)
    trades = []
    i = 30
    while i < len(x) - 1:
        signal = int(x.at[i, "signal"])
        atr = x.at[i, "atr14"]
        if signal == 0 or not np.isfinite(atr) or atr <= 0:
            i += 1
            continue
        entry_i = i + 1  # next bar open: no same-bar lookahead
        entry_bar = x.iloc[entry_i]
        entry_raw = float(entry_bar["open"])
        direction = "LONG" if signal == 1 else "SHORT"
        slip = slippage_bps / 10000
        entry = entry_raw * (1 + slip if signal == 1 else 1 - slip)
        risk_per_unit = float(atr) * stop_atr
        stop = entry - signal * risk_per_unit
        target = entry + signal * risk_per_unit * reward_risk
        risk_cash = capital * risk_pct
        qty = max(1, int(risk_cash / risk_per_unit))
        qty = min(qty, max(1, int(capital / max(entry, 0.01))))
        last_i = min(len(x) - 1, entry_i + (max_hold_bars or (12 if style == "intraday" else 60)))
        exit_i, exit_raw, reason = last_i, float(x.iloc[last_i]["close"]), "TIME"
        for j in range(entry_i, last_i + 1):
            bar = x.iloc[j]
            if style == "intraday" and j > entry_i and bar["session"] != x.iloc[j - 1]["session"]:
                exit_i, exit_raw, reason = j - 1, float(x.iloc[j - 1]["close"]), "SESSION_END"
                break
            hit_stop = float(bar["low"]) <= stop if signal == 1 else float(bar["high"]) >= stop
            hit_target = float(bar["high"]) >= target if signal == 1 else float(bar["low"]) <= target
            if hit_stop:  # conservative when both levels occur in same OHLC bar
                exit_i, exit_raw, reason = j, stop, "STOP"
                break
            if hit_target:
                exit_i, exit_raw, reason = j, target, "TARGET"
                break
        exit_price = exit_raw * (1 - slip if signal == 1 else 1 + slip)
        gross = (exit_price - entry) * qty * signal
        turnover = (abs(entry) + abs(exit_price)) * qty
        costs = turnover * (cost_bps_per_side / 10000)
        pnl = gross - costs
        trades.append({
            "symbol": symbol, "segment": segment, "style": style,
            "direction": direction, "entry_time": str(x.iloc[entry_i]["date"]),
            "exit_time": str(x.iloc[exit_i]["date"]), "entry": round(entry, 4),
            "exit": round(exit_price, 4), "stop": round(stop, 4),
            "target": round(target, 4), "quantity": qty, "exit_reason": reason,
            "gross_pnl": round(gross, 2), "costs": round(costs, 2),
            "net_pnl": round(pnl, 2), "risk_cash": round(risk_cash, 2),
        })
        i = max(i + 1, exit_i + 1)
    return trades


def init_replay_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id TEXT PRIMARY KEY, created_at TEXT, days INTEGER, timeframe TEXT,
            styles TEXT, instrument_count INTEGER, trade_count INTEGER,
            net_pnl REAL, win_rate REAL, profit_factor REAL, max_drawdown REAL,
            notes TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS backtest_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
            symbol TEXT, segment TEXT, style TEXT, direction TEXT,
            entry_time TEXT, exit_time TEXT, entry REAL, exit REAL,
            stop REAL, target REAL, quantity INTEGER, exit_reason TEXT,
            gross_pnl REAL, costs REAL, net_pnl REAL, risk_cash REAL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS replay_bars (
            run_id TEXT NOT NULL, symbol TEXT, segment TEXT, token TEXT,
            bar_time TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY(run_id, token, bar_time))""")


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"trade_count": 0, "net_pnl": 0.0, "win_rate": 0.0,
                "profit_factor": 0.0, "max_drawdown": 0.0}
    pnl = pd.Series([t["net_pnl"] for t in trades], dtype=float)
    gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    equity = pnl.cumsum()
    drawdown = equity - equity.cummax()
    return {
        "trade_count": int(len(pnl)), "net_pnl": round(float(pnl.sum()), 2),
        "win_rate": round(float((pnl > 0).mean() * 100), 2),
        "profit_factor": round(float(gains / losses), 3) if losses > 0 else (999.0 if gains > 0 else 0.0),
        "max_drawdown": round(float(drawdown.min()), 2),
    }


def run_historical_backtest(days: int = 90, timeframe: str = "FIVE_MINUTE",
                            styles: tuple[str, ...] = ("intraday", "swing"),
                            capital: float = 500_000, risk_pct: float = 0.005,
                            cost_bps_per_side: float = 3.0, slippage_bps: float = 1.0,
                            symbols: tuple[str, ...] | None = None) -> tuple[str, dict]:
    api = make_smart_api()
    master = load_instruments()
    run_id = uuid.uuid4().hex[:12]
    calendar_days = trading_days_to_calendar_days(days)
    universe = []
    for symbol in (symbols or settings.watchlist):
        row = cash_instrument(master, symbol)
        if row is not None:
            universe.append((str(row["token"]), symbol, "NSE", "NSE_CASH"))
    for name in ("NIFTY", "BANKNIFTY"):
        row = front_index_future(master, name)
        if row is not None:
            universe.append((str(row["token"]), str(row["symbol"]), "NFO", "INDEX_FUT"))
    all_trades = []
    bars_to_store = []
    for token, symbol, exchange, segment in universe:
        print(f"Downloading {symbol} ({exchange})...", flush=True)
        try:
            frame = fetch_history_days(api, token, exchange, calendar_days, timeframe)
        except Exception as exc:
            print(f"SKIP {symbol}: {exc}", flush=True)
            continue
        if frame.empty:
            print(f"SKIP {symbol}: no historical bars", flush=True)
            continue
        # Restrict to requested number of distinct trading sessions.
        sessions = frame["date"].dt.tz_convert(IST).dt.strftime("%Y-%m-%d")
        keep = sorted(sessions.unique())[-days:]
        frame = frame[sessions.isin(keep)].reset_index(drop=True)
        for row in frame.itertuples(index=False):
            bars_to_store.append((run_id, symbol, segment, token, str(row.date),
                                  float(row.open), float(row.high), float(row.low),
                                  float(row.close), float(row.volume)))
        for style in styles:
            trades = simulate_instrument(frame, symbol, segment, style, capital=capital,
                                         risk_pct=risk_pct, cost_bps_per_side=cost_bps_per_side,
                                         slippage_bps=slippage_bps)
            all_trades.extend(trades)
        time.sleep(0.35)
    summary = metrics(all_trades)
    init_replay_db(settings.db_path)
    with sqlite3.connect(settings.db_path) as con:
        con.executemany("INSERT OR REPLACE INTO replay_bars VALUES (?,?,?,?,?,?,?,?,?,?)", bars_to_store)
        con.executemany("""INSERT INTO backtest_trades
            (run_id,symbol,segment,style,direction,entry_time,exit_time,entry,exit,stop,target,
             quantity,exit_reason,gross_pnl,costs,net_pnl,risk_cash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [
            (run_id, t["symbol"], t["segment"], t["style"], t["direction"], t["entry_time"],
             t["exit_time"], t["entry"], t["exit"], t["stop"], t["target"], t["quantity"],
             t["exit_reason"], t["gross_pnl"], t["costs"], t["net_pnl"], t["risk_cash"])
            for t in all_trades
        ])
        con.execute("""INSERT INTO backtest_runs
            (run_id,created_at,days,timeframe,styles,instrument_count,trade_count,net_pnl,
             win_rate,profit_factor,max_drawdown,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
            run_id, datetime.now(IST).isoformat(timespec="seconds"), days, timeframe,
            ",".join(styles), len(universe), summary["trade_count"], summary["net_pnl"],
            summary["win_rate"], summary["profit_factor"], summary["max_drawdown"],
            "OHLCV-only heuristic replay; next-bar-open fills; conservative stop-first intrabar rule; indicative costs/slippage."
        ))
    return run_id, summary
