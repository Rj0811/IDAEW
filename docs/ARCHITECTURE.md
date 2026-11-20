# IADEW system architecture

## Goals
A Windows-first workstation for NSE cash equities and index futures. It detects candidate conditions, ranks them, explains evidence and alerts the trader. The trader approves and places orders manually.

## Components
1. Connectors: Kite Connect REST for instrument master/history and KiteTicker for live quotes; official NSE reports for aggregate participant context; GoCharting for visual footprint/DOM review.
2. Ingestion: normalize timestamps to Asia/Kolkata, maintain exchange calendar and instrument/expiry mapping, deduplicate and detect gaps.
3. Storage: SQLite for MVP; PostgreSQL/TimescaleDB when scale requires it.
4. Feature engine: OHLCV context, VWAP, time-of-day RVOL, relative traded value, EMA/ATR, volume profile and futures OI/basis. True delta/CVD/footprint require trade-level aggressor-side data.
5. Scanner: universe eligibility, market regime, candidate generation and ranking.
6. Signal engine: named setups, evidence, score, invalidation, expiry and duplicate suppression.
7. Risk engine: sizing, portfolio exposure, daily loss lockout, stale-data gate and manual kill switch.
8. Presentation: Streamlit MVP; later React/FastAPI; Telegram/desktop alerts.
9. Human execution: chart inspection and manual broker order entry. No order placement in v1.

## Data flow
flowchart TD
  K[Kite REST + WebSocket] --> N[Normalize and validate]
  X[NSE reports and licensed sources] --> N
  G[GoCharting visual review] --> H[Human confirmation]
  N --> S[(Market data store)]
  S --> F[Feature engine]
  F --> Q[Universe scanner]
  Q --> R[Setup and scoring engine]
  R --> Z[Risk gates]
  Z --> D[Dashboard and alerts]
  D --> H
  H --> M[Manual execution in Kite]
  M --> T[Trade journal and analytics]

## Deployment
- Windows 10/11 local workstation and Python virtual environment.
- .env for secrets; never commit it.
- SQLite in data/ for MVP; local backups.
- Structured logs with timestamp, source, instrument token, strategy version and data-quality state.

## Non-goals for v1
- No broker order placement.
- No claim to identify a bank, FII or individual institution.
- No scraping or reverse engineering of GoCharting.
- No synthetic footprint delta from candle volume.
