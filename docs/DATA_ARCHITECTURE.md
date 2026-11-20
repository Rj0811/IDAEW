# Data architecture and requirements

## MVP data
| Data | Resolution | Source/use |
|---|---|---|
| NSE cash OHLCV | 5m, 15m, 1D | Historical context and scanner |
| Index futures OHLCV | 5m, 15m, 1D | NIFTY/BANKNIFTY context |
| Instrument master | Daily | Tokens, expiry, lot/tick size |
| Live quotes | Streaming | Incremental updates and alerts |
| Market depth | Provider-supported | Displayed liquidity only |
| Futures OI | Historical/periodic | Position-change context |
| NSE reports | Daily/periodic | Aggregate participant context |

## Advanced data required for genuine order flow
- Trade-level prints with timestamp, price, quantity and aggressor side (or documented classification method).
- For footprint, aggregate aggressor buy/sell volume by price and bar.
- For order-book event analytics, sequenced add/modify/cancel/execute events and sufficient depth. A five-level snapshot is not a full order book.
- Provider permissions for storage, derived analytics and redistribution.

## Data contracts
Every record carries source, exchange, instrument_token, exchange_timestamp, received_timestamp, timezone, interval and quality_flags.

Quarantine stale ticks, unknown tokens, duplicate/out-of-order events where sequencing matters, invalid OHLC relationships, missing session data and expired futures contracts.

## Feature definitions
- RVOL_TOD: cumulative volume through current time divided by mean cumulative volume through the same time over prior comparable sessions.
- VWAP: sum(typical price * volume) / sum(volume), with session reset and documented price proxy.
- CVD: cumulative aggressive buy volume minus aggressive sell volume. Only compute with trade-side classification; document reset policy.
- OI change: change in OI for the same contract; never interpret in isolation.
- Basis: futures price minus spot; normalize for expiry/time-to-maturity and compare with historical distribution.

## GoCharting
Use GoCharting for visual review of footprint, CVD, volume profile, VWAP and DOM as available under the subscription. Do not assume a public API/export endpoint. Do not scrape or reverse engineer private endpoints. Any future connector must use documented and permitted interfaces.
