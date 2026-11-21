from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

@dataclass(frozen=True)
class Settings:
    angel_api_key: str = os.getenv("ANGEL_API_KEY", "")
    angel_client_code: str = os.getenv("ANGEL_CLIENT_CODE", "")
    angel_pin: str = os.getenv("ANGEL_PIN", "")
    angel_totp_secret: str = os.getenv("ANGEL_TOTP_SECRET", "")
    angel_jwt_token: str = os.getenv("ANGEL_JWT_TOKEN", "")
    angel_refresh_token: str = os.getenv("ANGEL_REFRESH_TOKEN", "")
    angel_feed_token: str = os.getenv("ANGEL_FEED_TOKEN", "")
    watchlist: tuple[str, ...] = tuple(
        s.strip().upper() for s in os.getenv(
            "CASH_WATCHLIST",
            "RELIANCE,HDFCBANK,ICICIBANK,SBIN,INFY,TCS,ITC,LT,AXISBANK,BAJFINANCE"
        ).split(",") if s.strip()
    )
    lookback_days: int = min(int(os.getenv("SCAN_LOOKBACK_DAYS", "45")), 100)
    min_avg_daily_value_cr: float = float(os.getenv("MIN_AVG_DAILY_VALUE_CR", "25"))
    min_price: float = float(os.getenv("MIN_PRICE", "50"))
    rvol_min: float = float(os.getenv("RVOL_MIN", "1.25"))
    db_path: Path = ROOT / "data" / "iadew.sqlite3"
    instrument_cache: Path = ROOT / "data" / "angelone_scrip_master.json"
    # NVIDIA NIM API
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_model: str = os.getenv("NVIDIA_MODEL", "z-ai/glm-5.3-flash")

settings = Settings()
