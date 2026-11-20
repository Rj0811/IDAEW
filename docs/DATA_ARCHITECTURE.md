# Data architecture and requirements

## Angel One source mapping
- Instrument master: official OpenAPIScripMaster JSON, refreshed daily and cached locally.
- NSE cash: exchange segment `NSE`; cash symbols generally resolve as `SYMBOL-EQ`.
- NSE derivatives: exchange segment `NFO`; index futures are selected by underlying name, futures instrument type and nearest unexpired expiry.
- Historical candles: SmartAPI `getCandleData` with exchange, symboltoken, interval, fromdate and todate.
- Live feed: SmartAPI WebSocket V2 with exchange type 1 for NSE cash and 2 for NFO.
- Session: JWT and feed tokens returned by TOTP-based SmartAPI login.

## MVP data
| Data | Resolution | Source/use |
|---|---|---|
| NSE cash OHLCV | 5m, 15m, 1D | SmartAPI historical candles |
| Index futures OHLCV | 5m, 15m, 1D | SmartAPI historical candles |
| Instrument master | Daily | Angel One scrip master |
| Live quotes | Streaming | SmartAPI WebSocket V2 |
| Market depth | Provider-supported | Displayed liquidity only |
| Futures OI | Historical/periodic | SmartAPI where returned for contract |
| NSE reports | Daily/periodic | Aggregate participant context |

## Advanced data required for genuine order flow
- Trade-level prints with timestamp, price, quantity and aggressor side (or documented classification method).
- For footprint, aggregate aggressor buy/sell volume by price and bar.
- For order-book event analytics, sequenced add/modify/cancel/execute events and sufficient depth. A quote/depth snapshot is not a full order-event feed.
- Provider permissions for storage, derived analytics and redistribution.

## Feature definitions
- RVOL_TOD: cumulative volume through current time divided by mean cumulative volume through the same time over prior comparable sessions.
- VWAP: sum(typical price * volume) / sum(volume), with session reset and documented price proxy.
- CVD: cumulative aggressive buy volume minus aggressive sell volume. Only compute with trade-side classification; document reset policy.
- OI change: change in OI for the same contract; never interpret in isolation.
- Basis: futures price minus spot; normalize for expiry/time-to-maturity and compare with historical distribution.

## Data quality
Every record carries source, exchange, instrument_token, exchange_timestamp, received_timestamp, timezone, interval and quality_flags. Quarantine stale ticks, unknown tokens, duplicate/out-of-order events where sequencing matters, invalid OHLC relationships, missing session data and expired futures contracts.

## Official documentation
Refer to Angel One SmartAPI documentation and official Python SDK. Respect the API's documented candle-window limits and request limits. Never hardcode symbol tokens; resolve from the daily scrip master.
