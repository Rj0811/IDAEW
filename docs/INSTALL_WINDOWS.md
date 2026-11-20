# Windows installation — Angel One

## Requirements
- Windows 10/11 64-bit
- Python 3.11 or newer
- Angel One account with SmartAPI access enabled
- SmartAPI API key and TOTP configured for the account
- GoCharting subscription for visual order-flow review

## Setup
Clone the repository and run these commands in PowerShell:

    git clone https://github.com/Rj0811/IDAEW.git C:\\IADEW
    cd C:\\IADEW
    py -3.11 -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Copy-Item .env.example .env

## Configure Angel One
1. Create/enable a SmartAPI app in the official Angel One SmartAPI developer portal.
2. Configure TOTP for your Angel One account and keep the TOTP secret private.
3. Fill these values in your local `.env`: `ANGEL_API_KEY`, `ANGEL_CLIENT_CODE`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET`.
4. Authenticate each trading day/session as required by Angel One:

       python auth.py

The helper writes JWT, refresh and feed tokens into the ignored local `.env`. Never commit or share this file. Do not paste credentials or OTP secrets into chat.

## Run scanner and dashboard

    python run_scanner.py
    streamlit run dashboard.py

The scanner downloads/caches Angel One's official OpenAPIScripMaster JSON, resolves NSE cash symbols and front-month NIFTY/BANKNIFTY futures, then requests 5-minute candles from SmartAPI.

## Important API notes
- SmartAPI candle requests use exchange, symboltoken, interval, fromdate and todate.
- The current 5-minute request is capped at 100 calendar days per request; this project defaults to 45.
- Historical responses contain timestamp, OHLC and volume; the scanner does not treat this as bid/ask footprint data.
- WebSocket V2 subscriptions use exchange type 1 for NSE cash and 2 for NFO.
- Verify current SmartAPI limits, account/API eligibility and session expiry behavior in official documentation before operational use.
- The current application is research/alert-only and contains no order-placement code.
