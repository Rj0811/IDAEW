from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("KITE_API_KEY", "")
    api_secret: str = os.getenv("KITE_API_SECRET", "")
    access_token: str = os.getenv("KITE_ACCESS_TOKEN", "")
    watchlist: tuple[str, ...] = tuple(
        s.strip().upper() for s in os.getenv(
            "CASH_WATCHLIST",
            "RELIANCE,HDFCBANK,ICICIBANK,SBIN,INFY,TCS,ITC,LT,AXISBANK,BAJFINANCE"
        ).split(",") if s.strip()
    )
    lookback_days: int = int(os.getenv("SCAN_LOOKBACK_DAYS", "45"))
    min_avg_daily_value_cr: float = float(os.getenv("MIN_AVG_DAILY_VALUE_CR", "25"))
    min_price: float = float(os.getenv("MIN_PRICE", "50"))
    rvol_min: float = float(os.getenv("RVOL_MIN", "1.25"))
    db_path: Path = ROOT / "data" / "iadew.sqlite3"
    instrument_cache: Path = ROOT / "data" / "instruments_nse.csv"

settings = Settings()
