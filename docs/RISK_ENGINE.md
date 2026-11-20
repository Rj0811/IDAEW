# Risk engine

The risk engine is independent of signal generation. A high score cannot bypass a risk block.

## Initial research defaults
- Risk per trade: 0.25%-0.50% of allocated trading capital.
- Daily loss lockout: 1.0%.
- Weekly loss review threshold: 2.5%.
- Max concurrent positions: 3.
- Correlated exposure: configurable sector/index buckets.
- Minimum planned reward/risk: 2.0, subject to setup testing.
- Max consecutive losses: 3 as a review/lockout trigger.

These are starting controls, not personalized financial advice or guaranteed safe levels.

## Sizing
Cash quantity = floor(risk budget / (entry - stop)), adjusted for tick size, costs and available capital.

Futures lots = floor(risk budget / (stop points * lot size)), then enforce margin, liquidity and aggregate exposure constraints.

## Mandatory gates
- Stop/invalidation defined before approval.
- Reject stale or incomplete data.
- Reject invalid/expired contracts and instruments under applicable restrictions.
- Deduplicate repeated signals.
- Enforce daily/weekly loss limits and portfolio exposure.
- Account for fees, slippage and gap risk.
- Manual kill switch and audit log.
- No automatic order placement in v1.

## Audit
Record decision timestamp, market snapshot reference, strategy version, planned risk, approval/rejection, actual fill, slippage, exit and costs.
