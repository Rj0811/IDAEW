from datetime import datetime, timedelta
import json
import time
import requests
import pandas as pd
from SmartApi import SmartConnect
from .config import settings

IST = "Asia/Kolkata"
SCRIP_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"

def make_smart_api() -> SmartConnect:
    if not settings.angel_api_key or not settings.angel_jwt_token:
        raise RuntimeError("Run python auth.py and set Angel One credentials in .env.")
    api = SmartConnect(api_key=settings.angel_api_key)
    api.setAccessToken(settings.angel_jwt_token)
    if settings.angel_refresh_token:
        api.setRefreshToken(settings.angel_refresh_token)
    if settings.angel_feed_token:
        api.setFeedToken(settings.angel_feed_token)
    if settings.angel_client_code:
        api.setUserId(settings.angel_client_code)
    return api

def load_instruments(api=None) -> pd.DataFrame:
    """Load the official daily Angel One scrip master and cache it locally."""
    path = settings.instrument_cache
    if path.exists() and time.time() - path.stat().st_mtime < 12 * 3600:
        rows = json.loads(path.read_text(encoding="utf-8"))
    else:
        response = requests.get(SCRIP_MASTER_URL, timeout=(15, 90))
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("Angel One scrip master returned an empty/unexpected payload.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows), encoding="utf-8")
    frame = pd.DataFrame(rows)
    required = {"token", "symbol", "name", "expiry", "instrumenttype", "exch_seg"}
    missing = required.difference(frame.columns)
    if missing:
        raise RuntimeError(f"Angel One scrip master missing columns: {sorted(missing)}")
    return frame

def history(api: SmartConnect, token: str, exchange: str, days: int,
            interval: str = "FIVE_MINUTE") -> pd.DataFrame:
    """Fetch candles; SmartAPI returns [timestamp, open, high, low, close, volume]."""
    days = min(max(int(days), 1), 100 if interval in {"FIVE_MINUTE", "TEN_MINUTE"} else 2000)
    now = datetime.now()
    start = now - timedelta(days=days)
    params = {
        "exchange": exchange,
        "symboltoken": str(token),
        "interval": interval,
        "fromdate": start.strftime("%Y-%m-%d %H:%M"),
        "todate": now.strftime("%Y-%m-%d %H:%M"),
    }
    response = api.getCandleData(params)
    if not response or response.get("status") is not True:
        message = (response or {}).get("message", "No response from Angel One historical API")
        code = (response or {}).get("errorcode", "")
        raise RuntimeError(f"Angel One candle API error {code}: {message}")
    rows = response.get("data") or []
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    frame = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.tz_convert(IST)
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["date", "open", "high", "low", "close", "volume"]).sort_values("date").reset_index(drop=True)

def cash_instrument(master: pd.DataFrame, symbol: str):
    rows = master[(master["exch_seg"].str.upper() == "NSE") &
                  (master["symbol"].str.upper() == f"{symbol.upper()}-EQ")]
    if rows.empty:
        rows = master[(master["exch_seg"].str.upper() == "NSE") &
                      (master["name"].str.upper() == symbol.upper()) &
                      (master["instrumenttype"].fillna("") == "")]
    return None if rows.empty else rows.iloc[0]

def front_index_future(master: pd.DataFrame, name: str):
    rows = master[(master["exch_seg"].str.upper() == "NFO") &
                  (master["name"].str.upper() == name.upper()) &
                  (master["instrumenttype"].str.upper() == "FUTIDX")].copy()
    if rows.empty:
        # Retain compatibility with scrip-master variants that label index futures as FUT.
        rows = master[(master["exch_seg"].str.upper() == "NFO") &
                      (master["name"].str.upper() == name.upper()) &
                      (master["instrumenttype"].str.upper() == "FUT")].copy()
    if rows.empty:
        return None
    rows["expiry_date"] = pd.to_datetime(rows["expiry"], errors="coerce").dt.date
    today = pd.Timestamp.now(tz=IST).date()
    rows = rows[rows["expiry_date"].notna() & (rows["expiry_date"] >= today)].sort_values("expiry_date")
    return None if rows.empty else rows.iloc[0]
