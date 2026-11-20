# Scanner specification

## Universe
- Liquid NSE cash equities from a configurable instrument list.
- Front-month NIFTY and BANKNIFTY futures, with expiry and contract validation.
- Later: stock futures with liquidity, ban/restriction and expiry filters.

## Initial eligibility defaults (configurable research values)
- Average daily traded value >= INR 25 crore.
- Price >= INR 50.
- Time-of-day RVOL >= 1.25.
- Historical lookback 20-45 sessions.
- Exclude stale/incomplete bars and wide spreads where quote data exists.

## MVP features
1. Time-of-day matched cumulative RVOL.
2. Session VWAP from completed bars.
3. EMA 9/20 trend context.
4. Intraday return from session open.
5. Average daily traded value.
6. Candidate ranking and explanatory feature columns.

## Initial score (0-100 heuristic; not probability)
- RVOL: 30
- EMA trend: 20
- VWAP position: 20
- Intraday momentum: 15
- Liquidity/traded value: 15

Score ranks candidates only. Hard filters override score: stale data, no stop/invalidation, insufficient liquidity, risk lockout, contract expiry issue or missing required features.

## Advanced setup candidates
- Liquidity sweep + absorption + reclaim.
- Initiative breakout + acceptance + retest.
- Failed auction / breakout trap.
- Trend pullback with execution confirmation.

Every setup records direction, timeframe, trigger, invalidation, targets, evidence, data quality, expiry and strategy version.

## Validation
Avoid look-ahead bias; use completed bars for bar-close signals. Compare time-of-day volume with like-for-like sessions. Include brokerage, taxes, slippage, impact and gaps. Keep in-sample, validation and out-of-sample periods separate. Report expectancy, profit factor, drawdown, MAE/MFE, slippage and regime breakdown.
