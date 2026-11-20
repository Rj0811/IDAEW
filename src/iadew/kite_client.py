from datetime import datetime, timedelta
import time
import pandas as pd
from kiteconnect import KiteConnect
from .config import settings

def make_kite() -> KiteConnect:
    if not settings.api_key or not settings.access_token:
        raise RuntimeError("Set KITE_API_KEY and KITE_ACCESS_TOKEN in .env.")
    kite = KiteConnect(api_key=settings.api_key)
    kite.set_access_token(settings.access_token)
    return kite

def load_instruments(kite: KiteConnect, exchange: str = "NSE") -> pd.DataFrame:
    if exchange == "NSE" and settings.instrument_cache.exists():
        age = time.time() - settings.instrument_cache.stat().st_mtime
        if age < 12 * 3600:
            return pd.read_csv(settings.instrument_cache)
    df = pd.DataFrame(kite.instruments(exchange))
    if exchange == "NSE":
        settings.instrument_cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(settings.instrument_cache, index=False)
    return df

def history(kite: KiteConnect, token: int, days: int, interval: str = "5minute",
            oi: bool = False) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    rows = kite.historical_data(int(token), start, end, interval, continuous=False, oi=oi)
    time.sleep(0.35)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    if df["date"].dt.tz is None:
        df["date"] = df["date"].dt.tz_localize("Asia/Kolkata")
    else:
        df["date"] = df["date"].dt.tz_convert("Asia/Kolkata")
    return df.sort_values("date").reset_index(drop=True)
