# Implementation roadmap

## Phase 0 — Angel One setup
- Enable SmartAPI and create API key.
- Configure TOTP; store API key, client code, PIN and TOTP secret in local `.env`.
- Run `python auth.py` and validate session tokens.
- Download/cache official daily scrip master.

## Phase 1 — Historical scanner MVP
- Resolve NSE cash instruments and front-month NIFTY/BANKNIFTY futures from Angel One tokens.
- Fetch historical 5m candles within documented per-request limits.
- Calculate time-of-day RVOL, VWAP, EMA 9/20, momentum and traded value.
- Persist scans to SQLite and display via Streamlit.
- Compare results with charts and document false positives.

## Phase 2 — Live ingestion
- Subscribe to Angel One SmartAPI WebSocket V2 using NSE/NFO exchange types.
- Add reconnect/backoff, heartbeat and feed-health monitoring.
- Normalize exchange timestamps to Asia/Kolkata.
- Build completed 1m/5m bars from ticks and reconcile with historical bars.
- Add data freshness, gap and duplicate checks.

## Phase 3 — Execution analytics
- Validate available trade-level data and licensing.
- Add aggressor-side delta/CVD only with suitable trade prints.
- Add footprint aggregation, imbalance and absorption candidates.
- Add volume profile, liquidity sweep and futures OI/basis context.
- Keep GoCharting visual confirmation independent unless documented integration exists.

## Phase 4 — Signals and alerts
- Implement named setups and evidence objects.
- Add score, hard risk filters, signal expiry and deduplication.
- Add Telegram/desktop notifications.
- Add manual approval and trade journal.

## Phase 5 — Validation
- Historical replay and realistic cost/slippage model.
- Walk-forward and out-of-sample testing.
- Paper trade for at least 20 sessions as an initial operational check.
- Evaluate expectancy, profit factor, max drawdown, MAE/MFE and setup/regime breakdown.

## Phase 6 — Production hardening
- Local backups, structured logs, monitoring and recovery.
- Windows Task Scheduler for market-session jobs.
- Document data licensing, provider terms and retention.
- Keep order routing disabled unless separately reviewed for broker, exchange and SEBI requirements.
