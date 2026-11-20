from pathlib import Path
from dotenv import set_key
from kiteconnect import KiteConnect
from src.iadew.config import ROOT, settings

def main():
    if not settings.api_key or not settings.api_secret:
        raise SystemExit("Set KITE_API_KEY and KITE_API_SECRET in .env first.")
    kite = KiteConnect(api_key=settings.api_key)
    print("Open this URL, sign in to Zerodha and authorize the app:")
    print(kite.login_url())
    request_token = input("Paste request_token from the redirect URL: ").strip()
    if not request_token:
        raise SystemExit("No request_token supplied.")
    session = kite.generate_session(request_token, api_secret=settings.api_secret)
    set_key(str(ROOT / ".env"), "KITE_ACCESS_TOKEN", session["access_token"])
    print("Access token saved to local .env. Keep this file private.")
    print("Repeat the login when the session token expires.")

if __name__ == "__main__":
    main()
