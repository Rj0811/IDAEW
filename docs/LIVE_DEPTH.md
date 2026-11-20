# Live depth collection

IADEW supports an explicit NSE cash Depth20 collection mode using Angel One
SmartAPI WebSocket V2 mode 4.

## Run

After authenticating with `python auth.py`, start:

```powershell
python run_live_feed.py --depth
```

This run subscribes only to the NSE cash symbols in the configured watchlist.
The official Angel One Python SDK currently validates Depth mode as exchange
type 1 (NSE cash) and enforces a maximum of 50 tokens per depth subscription.
It does not include the NFO index futures in this mode. Run the ordinary
`python run_live_feed.py` separately when you need the existing quote/candle
collector; do not run two collectors against the same WebSocket session unless
your account's connection limits permit it.

## Storage

Each received packet is appended to SQLite table `depth_snapshots` with:
token, exchange type, exchange timestamp (when supplied), local received
timestamp, normalized rupee prices, quantities, order counts, source and a
basic completeness flag. Snapshots are retained as received; they are not
collapsed into candles.

The dashboard's depth panel reads the latest stored snapshot per token.
An empty table means no depth packet has yet been persisted; verify the session,
market hours, watchlist size and SmartAPI subscription response.

## Interpretation limits

- These are periodic depth snapshots, not sequenced add/modify/cancel/execute
  order events. Do not infer queue position or full liquidity replenishment.
- Depth quantities and order counts describe displayed book levels at snapshot
  time; they do not establish trade aggressor side.
- This feed does not provide the trade prints needed to claim true footprint
  delta or CVD. Keep GoCharting as the visual footprint/CVD confirmation tool
  until a documented trade-level feed is available.


## Snapshot-based analytics

The dashboard calculates:
- Best bid, best ask, spread, midpoint and quantity-weighted midpoint.
- Bid and ask displayed quantities across the top 5, 10 and 20 levels.
- Depth imbalance as (bid quantity - ask quantity) / total displayed quantity.
- Quantity changes at identical price levels between the latest two stored snapshots.

A positive imbalance means more displayed bid quantity in the selected depth window;
a negative value means more displayed ask quantity. This is a book-state metric,
not a directional trade signal. A level disappearing or shrinking between snapshots
is labelled as reduced/absent displayed liquidity; it is not proof of cancellation
because an execution, repricing, feed sampling gap or other event may explain it.

Unit tests: `python -m unittest tests.test_depth_analytics`.


## Rolling pressure monitor

The dashboard now evaluates the latest stored snapshots over rolling 1-minute and
5-minute windows. For top 5, 10 and 20 levels it reports mean imbalance and the
share of samples with strong bid dominance (imbalance >= +15%) or ask dominance
(imbalance <= -15%). It also flags near/deep disagreement when top-5 imbalance
is at least +15% while top-20 is at most -10%, or the inverse.

A divergence observation is surfaced only after at least three snapshots are
available in the selected rolling window. It is an observation alert only; it
does not enter scanner scores, recommend a trade, or place orders. Snapshot
frequency and missing packets affect the persistence estimate. The rolling
window uses local received timestamps because the depth packet may not supply
an exchange timestamp.

Tests: `python -m unittest discover -s tests`.


## Forward price validation

Run the combined depth + quote collector during market hours:

```powershell
python run_live_feed.py --depth
```

In this mode, one WebSocket subscribes to NSE cash Depth20 and Quote mode.
Quote packets are aggregated into 1m/5m candles in `live_bars`, while depth
packets are appended to `depth_snapshots`. This provides same-instrument
timestamps for descriptive evaluation. The existing no-argument collector
continues to work as quote-only mode.

After collecting several sessions:

```powershell
python run_depth_validation.py --days 5
```

The script exports matched observations and grouped summaries under `reports/`.
It groups top-5/10/20 imbalance into ask-heavy, balanced and bid-heavy buckets,
then measures 1m and 5m subsequent candle-close returns. It also compares
near/deep divergence observations. Baseline and forward prices use the first
available 1m candle at or after the snapshot/horizon; this is approximate
because the stored bar timestamp labels the minute bucket, not the exact
intraminute quote time.

Interpretation limits:
- Require adequate samples across multiple sessions; one day's results are noisy.
- No spread, brokerage, slippage, queue position or executable fills are modeled.
- Returns are association, not causation or a predictive edge.
- No thresholds are fed into trade scoring or order execution.
