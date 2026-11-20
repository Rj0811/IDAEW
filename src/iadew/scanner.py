from datetime import datetime
import sqlite3
import numpy as np
import pandas as pd
from .config import settings
from .kite_client import make_kite, load_instruments, history

IST = "Asia/Kolkata"

def _session(series):
    return series.dt.tz_convert(IST).dt.strftime("%Y-%m-%d")

def _slot(series):
    return series.dt.tz_convert(IST).dt.strftime("%H:%M")

def summarise(df, symbol, segment):
    if df.empty or len(df) < 25:
        return None
    x = df.copy()
    x["session"] = _session(x["date"])
    x["slot"] = _slot(x["date"])
    today = pd.Timestamp.now(tz=IST).strftime("%Y-%m-%d")
    current = x[x.session == today].copy()
    prior = x[x.session < today].copy()
    if current.empty or prior.session.nunique() < 5:
        return None
    current = current[current.date < pd.Timestamp.now(tz=IST).floor("5min")]
    if len(current) < 3:
        return None
    current = current.sort_values("date")
    last = current.iloc[-1]
    current_vol = float(current.volume.sum())
    hist_cum = []
    for _, day in prior.groupby("session"):
        same_time = day[day.slot <= last.slot]
        if not same_time.empty:
            hist_cum.append(float(same_time.volume.sum()))
    if len(hist_cum) < 5:
        return None
    avg_cum = float(np.mean(hist_cum))
    rvol = current_vol / avg_cum if avg_cum else np.nan
    typical = (current.high + current.low + current.close) / 3
    vol_sum = float(current.volume.sum())
    vwap = float((typical * current.volume).sum() / vol_sum) if vol_sum else np.nan
    close = current.close.astype(float)
    ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    price = float(last.close)
    day_open = float(current.iloc[0].open)
    day_return = ((price / day_open) - 1) * 100 if day_open else 0.0
    daily_value = (prior.assign(tv=((prior.high + prior.low + prior.close) / 3) * prior.volume)
                   .groupby("session").tv.sum())
    avg_value = float(daily_value.tail(20).mean()) if not daily_value.empty else 0.0
    score_rvol = min(max((rvol - 1.0) / 1.5, 0), 1) * 30
    score_liquidity = 15 if avg_value >= settings.min_avg_daily_value_cr * 1e7 else 0

    # Direction-specific scores avoid structurally suppressing bearish candidates.
    bull_trend = 20 if ema9 > ema20 and price > ema20 else (10 if ema9 > ema20 or price > ema20 else 0)
    bear_trend = 20 if ema9 < ema20 and price < ema20 else (10 if ema9 < ema20 or price < ema20 else 0)
    bull_vwap = 20 if price > vwap else 0
    bear_vwap = 20 if price < vwap else 0
    bull_momentum = min(max((day_return + 0.5) / 1.5, 0), 1) * 15
    bear_momentum = min(max((-day_return + 0.5) / 1.5, 0), 1) * 15
    bull_score = round(score_rvol + bull_trend + bull_vwap + bull_momentum + score_liquidity, 1)
    bear_score = round(score_rvol + bear_trend + bear_vwap + bear_momentum + score_liquidity, 1)
    score = max(bull_score, bear_score)
    bias = "BULLISH_CANDIDATE" if bull_score >= bear_score else "BEARISH_CANDIDATE"
    if score < 65:
        bias = "WATCH"
    return {
        "symbol": symbol, "segment": segment, "timestamp": str(last.date),
        "price": round(price, 2), "day_return_pct": round(day_return, 2),
        "rvol": round(float(rvol), 2), "vwap": round(vwap, 2),
        "ema9": round(ema9, 2), "ema20": round(ema20, 2),
        "avg_daily_value_cr": round(avg_value / 1e7, 2), "score": score,
        "bull_score": bull_score, "bear_score": bear_score, "bias": bias,
        "data_note": "5m OHLCV-derived; not bid/ask footprint delta"
    }

def init_db():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.db_path) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS scan_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT, scan_time TEXT NOT NULL,
        symbol TEXT NOT NULL, segment TEXT NOT NULL, timestamp TEXT,
        price REAL, day_return_pct REAL, rvol REAL, vwap REAL, ema9 REAL,
        ema20 REAL, avg_daily_value_cr REAL, score REAL, bias TEXT, data_note TEXT
        )""")

def save(rows):
    init_db()
    scan_time = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(settings.db_path) as con:
        for r in rows:
            con.execute("""INSERT INTO scan_results
            (scan_time,symbol,segment,timestamp,price,day_return_pct,rvol,vwap,
             ema9,ema20,avg_daily_value_cr,score,bias,data_note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (scan_time,r["symbol"],r["segment"],r["timestamp"],r["price"],
             r["day_return_pct"],r["rvol"],r["vwap"],r["ema9"],r["ema20"],
             r["avg_daily_value_cr"],r["score"],r["bias"],r["data_note"]))

def _front_future(kite, name):
    nfo = pd.DataFrame(kite.instruments("NFO"))
    if nfo.empty:
        return None
    today = pd.Timestamp.now(tz=IST).date()
    f = nfo[(nfo.name == name) & (nfo.instrument_type == "FUT")].copy()
    if f.empty:
        return None
    f["expiry"] = pd.to_datetime(f.expiry).dt.date
    f = f[f.expiry >= today].sort_values("expiry")
    if f.empty:
        return None
    row = f.iloc[0]
    return int(row.instrument_token), str(row.tradingsymbol)

def run_scan():
    kite = make_kite()
    nse = load_instruments(kite, "NSE")
    rows = []
    for symbol in settings.watchlist:
        found = nse[nse.tradingsymbol == symbol]
        if found.empty:
            print(f"SKIP {symbol}: not found")
            continue
        try:
            token = int(found.iloc[0].instrument_token)
            bars = history(kite, token, settings.lookback_days, "5minute")
            result = summarise(bars, symbol, "NSE_CASH")
            if result and result["price"] >= settings.min_price and result["avg_daily_value_cr"] >= settings.min_avg_daily_value_cr * 1.0 and result["rvol"] >= settings.rvol_min:
                rows.append(result)
            print(f"Scanned {symbol}")
        except Exception as exc:
            print(f"ERROR {symbol}: {exc}")
    for name in ("NIFTY", "BANKNIFTY"):
        try:
            contract = _front_future(kite, name)
            if not contract:
                continue
            token, tradingsymbol = contract
            bars = history(kite, token, settings.lookback_days, "5minute", oi=True)
            result = summarise(bars, tradingsymbol, "INDEX_FUT")
            if result and result["rvol"] >= settings.rvol_min:
                rows.append(result)
            print(f"Scanned {tradingsymbol}")
        except Exception as exc:
            print(f"ERROR {name} FUT: {exc}")
    rows.sort(key=lambda item: item["score"], reverse=True)
    save(rows)
    if rows:
        pd.DataFrame(rows).to_csv("data/latest_scan.csv", index=False)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    output = run_scan()
    print(output.to_string(index=False) if not output.empty else "No qualifying candidates.")
