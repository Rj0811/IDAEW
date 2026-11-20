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

## Portfolio accounting (shared-capital revision)

- Signals are generated per instrument/style, then candidates are allocated in entry-time order against one shared portfolio.
- Each accepted position consumes full entry notional from available capital until its exit. Quantity is the minimum of risk-budget sizing and available-notional sizing, rounded down to the instrument lot size.
- `risk_budget` is the equity-based risk ceiling; `actual_risk` is stop distance × allocated quantity. They are intentionally separate because capital/notional/lot constraints can reduce actual risk below the budget.
- `allocated_capital` is full notional reserved while a position is open. This is a conservative cash-notional constraint, not Angel One margin simulation.
- Portfolio net P&L, ending equity, profit factor and drawdown are calculated from accepted, sized trades in exit-time order. Dashboard includes strategy-wise and instrument-wise breakdowns.
- The backtest stores the requested lookback and replay bars; inspect each run’s min/max bar timestamps to confirm actual data coverage.

## Metrics

- Net P&L after configured estimated costs.
- Win rate.
- Profit factor (winning net P&L divided by absolute losing net P&L).
- Maximum peak-to-trough drawdown of the realized portfolio equity curve, starting from configured capital.

Metrics aggregate accepted positions across the configured instruments and strategy styles. Use the dashboard style filter and breakdown tables to inspect them separately.

## Important limitations

1. OHLCV bars do not reveal aggressor side, bid/ask delta, footprint, absorption or full order-book events.
2. Current front-month futures are not a continuous back-adjusted futures history. Expiry roll and contract-specific history need dedicated treatment.
3. Futures quantities are rounded to the lot size in the instrument master, but positions must fit full contract notional inside available portfolio cash. This is not broker margin treatment and may reject futures that would otherwise be margin-tradable. Expiry roll and continuous-contract stitching are not implemented.
4. Costs and slippage are generic basis-point assumptions, not a live Angel One brokerage/tax calculator.
5. OHLC bars cannot reveal the order of intrabar high/low events. The conservative stop-first rule is applied if stop and target are both touched.
6. No broker orders are sent. This is a historical paper backtest only.
7. Backtest metrics are not forecasts or guarantees. Validate with out-of-sample periods, walk-forward analysis, and realistic costs before using signals.

## Next improvements

- Broker-specific futures margin estimates and continuous futures contract stitching.
- Walk-forward train/test splits and benchmark comparison.
- Portfolio-level position, sector and correlated-risk controls.
- Strategy parameter versioning and experiment tracking.
- Separate intraday and swing equity curves.
- Licensed trade-level data before adding footprint/CVD/absorption signals.
