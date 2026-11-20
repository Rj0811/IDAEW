# Windows installation

## Requirements
- Windows 10/11 64-bit
- Python 3.11 or newer
- Zerodha Kite Connect data access as required for historical and streaming data
- GoCharting subscription for visual order-flow review

## Setup
1. Extract/clone the repository to C:\\IADEW.
2. Open PowerShell in the repository directory.
3. Create and activate a virtual environment.
4. Install dependencies.
5. Copy .env.example to .env and add Kite credentials locally.

PowerShell commands:

    py -3.11 -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Copy-Item .env.example .env

## Kite authentication
Create a Kite Connect app through the official developer portal, configure the redirect URL required by the current API workflow, and use the official kiteconnect SDK login flow. Access tokens are session-based; follow Zerodha's current authentication documentation. Do not hardcode API secrets.

## Run
    python run_scanner.py
    streamlit run dashboard.py

## Operational cautions
- Verify current Kite API pricing, rate limits, historical intervals and WebSocket terms before subscribing.
- Cache historical data; do not refetch a multi-week history on every scan.
- Respect exchange holidays and market sessions.
- The current scanner is alert/research-only and contains no order-placement code.
- Initial scanner features are derived from 5-minute OHLCV. It does not calculate genuine footprint delta/CVD.
