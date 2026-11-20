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
