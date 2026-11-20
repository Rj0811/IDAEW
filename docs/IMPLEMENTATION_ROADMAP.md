# Implementation roadmap

## Phase 0 — Local setup
- Install Python 3.11+, VS Code and Git on Windows.
- Create venv and install requirements.
- Create Kite Connect app and authenticate.
- Store credentials only in .env; never commit them.

## Phase 1 — Historical scanner MVP
- Refresh NSE/NFO instrument master.
- Build configurable cash watchlist and front-month index futures mapping.
- Fetch historical 5m bars within API limits.
- Calculate time-of-day RVOL, VWAP, EMA 9/20, momentum and traded value.
- Persist scans to SQLite and display via Streamlit.
- Compare results with charts and document false positives.

## Phase 2 — Live ingestion
- Add KiteTicker WebSocket with reconnect/backoff and heartbeat.
- Normalize timestamps to Asia/Kolkata.
- Build completed 1m/5m bars from ticks and reconcile with historical bars.
- Add data freshness, gap and duplicate checks.
- Cache historical data; avoid repeated large downloads.

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
- Tune only on training/validation data, then freeze parameters for out-of-sample test.

## Phase 6 — Production hardening
- Local backups, structured logs, monitoring and recovery.
- Windows Task Scheduler for market-session jobs.
- Document data licensing, provider terms and retention.
- Keep order routing disabled unless separately reviewed for broker, exchange and SEBI requirements.

## Acceptance criteria
- Scanner reproducibly produces same output from same input data.
- Missing/stale data suppresses alerts.
- Every signal has traceable evidence and strategy version.
- No signal bypasses risk gates.
- Paper-trading results include costs and realistic fill assumptions.
