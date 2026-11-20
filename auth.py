import sys
from dotenv import set_key
import pyotp
from SmartApi import SmartConnect
from src.iadew.config import ROOT, settings

ENV_FILE = ROOT / ".env"

def main():
    required = {
        "ANGEL_API_KEY": settings.angel_api_key,
        "ANGEL_CLIENT_CODE": settings.angel_client_code,
        "ANGEL_PIN": settings.angel_pin,
        "ANGEL_TOTP_SECRET": settings.angel_totp_secret,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise SystemExit("Add these values to your local .env first: " + ", ".join(missing))

    totp = pyotp.TOTP(settings.angel_totp_secret).now()
    smart_api = SmartConnect(api_key=settings.angel_api_key)
    session = smart_api.generateSession(
        settings.angel_client_code,
        settings.angel_pin,
        totp,
    )
    if not session or session.get("status") is not True:
        raise SystemExit(f"Angel One login failed: {(session or {}).get('message', 'unknown error')}")

    # Persist only the session tokens in the ignored local .env file.
    set_key(str(ENV_FILE), "ANGEL_JWT_TOKEN", smart_api.access_token or "")
    set_key(str(ENV_FILE), "ANGEL_REFRESH_TOKEN", smart_api.refresh_token or "")
    set_key(str(ENV_FILE), "ANGEL_FEED_TOKEN", smart_api.feed_token or "")
    print("Angel One SmartAPI login successful.")
    print("Session tokens saved to local .env (ignored by Git).")
    print("SmartAPI sessions are time-limited; authenticate again when they expire.")

if __name__ == "__main__":
    main()
