# Historical replay and paper trading

## Scope

The first replay milestone uses Angel One 5-minute OHLCV for the configured NSE cash watchlist and the current front-month NIFTY/BANKNIFTY futures. Default run is 90 trading sessions, both intraday and swing strategies. The command is local and does not place orders.

## Run

1. Install project dependencies: `pip install -r requirements.txt`.
2. Authenticate: `python auth.py`.
3. Run: `python run_backtest.py --days 90 --timeframe FIVE_MINUTE --style both`.
4. Review results in `streamlit run dashboard.py`, under Historical replay & paper trading.

Optional CLI controls: `--capital`, `--risk-pct`, `--cost-bps`, and `--slippage-bps`. The defaults are ₹500,000 capital, 0.5% risk budget per trade, 3 bps estimated cost per side and 1 bp slippage per side. These are adjustable research assumptions, not trading recommendations.

## Data acquisition

The requested number of sessions is converted to a calendar lookback with a buffer for weekends and holidays. Historical requests are split into windows of no more than 90 calendar days. Returned rows are deduplicated by exchange timestamp, sorted, and trimmed to the latest requested number of distinct sessions. Some symbols may return fewer sessions or no data; the CLI prints a skip message and continues.

The run stores downloaded bars and results in the local SQLite database:
- `replay_bars`: downloaded OHLCV by run, instrument and timestamp.
- `backtest_runs`: run configuration and aggregate metrics.
- `backtest_trades`: simulated entries, exits, stops, targets, costs and P&L.

## Strategy definitions

### Intraday

- Long: previous close at/below EMA9, current close crosses above EMA9, EMA9 above EMA20 and close above session VWAP.
- Short: inverse conditions.
- Signal is evaluated at close and entered at next bar open.
- No position is carried overnight. A signal on the last bar of a session is skipped if the next available bar belongs to a new session.

### Swing

- Long: close breaks above the prior 20-bar high while EMA9 > EMA20.
- Short: close breaks below the prior 20-bar low while EMA9 < EMA20.
- Signal at close, next-bar-open entry, maximum 60 five-minute bars.

Both use ATR(14) x 1.5 initial stop and a 2R target. If both stop and target are touched in the same OHLC bar, the stop is assumed to execute first. Only one position per instrument/style is simulated at a time.

## Metrics

- Net P&L after configured estimated costs.
- Win rate.
- Profit factor (gross winning net trades divided by absolute losing net trades).
- Maximum peak-to-trough drawdown of the trade-level cumulative P&L curve.

Metrics aggregate the configured instruments and both strategy styles. Use the dashboard style filter to inspect each style separately.

## Important limitations

1. OHLCV bars do not reveal aggressor side, bid/ask delta, footprint, absorption or full order-book events.
2. Current front-month futures are not a continuous back-adjusted futures history. Expiry roll and contract-specific history need dedicated treatment.
3. Futures sizing is simplified and does not yet enforce actual lot size, margin, expiry, or portfolio exposure. Futures P&L is indicative only.
4. Costs and slippage are generic basis-point assumptions, not a live Angel One brokerage/tax calculator.
5. OHLC bars cannot reveal the order of intrabar high/low events. The conservative stop-first rule is applied if stop and target are both touched.
6. No broker orders are sent. This is a historical paper backtest only.
7. Backtest metrics are not forecasts or guarantees. Validate with out-of-sample periods, walk-forward analysis, and realistic costs before using signals.

## Next improvements

- Continuous futures contract stitching and correct lot-size/margin sizing.
- Walk-forward train/test splits and benchmark comparison.
- Portfolio-level position, sector and correlated-risk controls.
- Strategy parameter versioning and experiment tracking.
- Separate intraday and swing equity curves.
- Licensed trade-level data before adding footprint/CVD/absorption signals.
