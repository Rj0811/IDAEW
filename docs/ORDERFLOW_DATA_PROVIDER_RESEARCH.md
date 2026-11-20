# Order-flow data provider qualification

**Status:** Preliminary desk research; no provider selected and no new subscription approved.  
**Research date:** 21 November 2026  
**Purpose:** Identify a documented, licensed source for IADEW's genuine trade-level order-flow research.

## What IADEW actually needs

A qualifying source should demonstrate, with sample records and written documentation:

1. Individual executed trades/prints with exchange timestamp, price and quantity.
2. A documented aggressor-side field (buyer-initiated / seller-initiated), or enough quote/trade sequencing to reproduce the provider's classification method.
3. Historical access suitable for research and replay, with clear retention and instrument/segment coverage.
4. Live streaming with stable identifiers, sequence/gap handling and timestamps.
5. For order-book event research: sequenced add/modify/cancel/execute events, not just periodic depth snapshots.
6. Explicit rights for local storage, derived analytics, backtesting and any permitted display.
7. Total price, taxes, connection limits, rate limits, support and trial/sample terms.

**Acceptance rule:** A feed that only provides OHLCV, one-second quote snapshots, or depth snapshots without trade aggressor classification is not a true footprint/CVD source. Do not infer aggressor side from candle direction or displayed depth.

## Preliminary provider matrix

| Source | Publicly documented capability | What is not yet established | Current IADEW stance |
|---|---|---|---|
| Angel One SmartAPI | Historical candles; live quote stream; supported live NSE cash Depth20 snapshots | Historical depth archive, individual historical prints and exchange-confirmed aggressor side | Keep as current candle + prospective depth source; not a true CVD source |
| GoCharting | NSE/BSE F&O footprint/cluster charts, delta/CVD and order-flow tools; chart export, replay and webhook alerts are described in public materials | Whether export includes raw per-price bid/ask executed volume; whether there is a supported API/export for footprint history; webhook payloads are alerts, not a documented raw feed | Keep for visual confirmation. Ask support for exact export/API capability before designing an integration |
| Accelpix | Public docs advertise live tick-by-tick and historical tick APIs; sample tick records show timestamp, price, volume and OI | Whether each record is an individual exchange trade or a quote/tick update; aggressor-side classification; bid/ask-at-trade; historical retention by instrument/segment; depth/order-event access; price and licence | Strong candidate for a sample-data evaluation, not yet qualified |
| Global Datafeeds | Public docs advertise one-second realtime bid/ask/trade updates and historical Tick/Minute/EOD APIs; documentation describes a limited historical tick backfill window for NSE cash | Whether historical ticks are individual prints or sampled updates; aggressor-side classification and methodology; depth/order-event history; precise segment-wise retention and commercial licence | Candidate for sample-data evaluation, not yet qualified |
| NSE Data & Analytics direct | Official materials describe real-time feed levels including Level 1/2/3 and tick-by-tick, plus historical order/trade data offerings | Commercial pricing, access/connection requirements, permitted usage and exact delivery format for this use case | Highest-authority route to investigate if vendor feeds cannot meet the requirements; likely more operationally involved |

## Public documentation reviewed

- GoCharting documentation index: https://docs.gocharting.com/
- GoCharting cluster/footprint chart: https://docs.gocharting.com/docs/charting/chart-types/cluster-aka-footprint-chart
- GoCharting bar statistics: https://docs.gocharting.com/docs/orderflow/bar-statistics
- GoCharting layout / Excel download control: https://docs.gocharting.com/docs/general-settings/layout-setup
- Accelpix Python API history and tick docs: https://support.accelpix.com/portal/en/kb/articles/pix-apis-realtime-and-historical-data-in-python
- Accelpix product API overview: https://www.accelpix.com/products/pix-api/
- Global Datafeeds data availability: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/introduction/type-of-data-available/
- Global Datafeeds GetHistory: https://globaldatafeeds.in/global-datafeeds-apis/global-datafeeds-apis/rest-api-documentation/function-gethistory/
- NSE paid real-time data: https://www.nseindia.com/static/market-data/real-time-data-subscription
- NSE historical order/trade data: https://betanseapi.nseindia.com/static/market-data/eod-historical-data-subscription

## Questions to send providers

### GoCharting
- Can the Excel/CSV chart export export footprint/cluster data at each price level, including bid volume, ask volume, total volume and delta?
- Can this be exported for historical/replayed bars and expired NIFTY/BANKNIFTY contracts?
- Is there a documented API, file export, or webhook that exposes those numeric records? Please share schema and sample.
- Does the India feed's buy/sell classification represent exchange aggressor side, quote-based classification, or another methodology?
- What are the retention limits and terms for storing exported data and using it in a private research application?

### Accelpix and Global Datafeeds
- Please provide a raw sample for NIFTY futures and one liquid NSE stock, both live and historical.
- Does each row represent an individual executed trade, a quote update, or a sampled/aggregated tick?
- Are trade price, trade quantity, exchange timestamp, best bid/ask and aggressor side provided on the same event?
- If aggressor side is derived, provide the exact classification method and handling of locked/crossed/stale quotes and unclassified trades.
- What is the historical tick retention by NSE cash, index futures and stock futures? Can data be retrieved for expired contracts?
- Is historical depth available? Are there sequenced order add/modify/cancel/execute events, or only snapshots?
- What are API limits, simultaneous subscriptions, latency expectations, monthly/annual cost, taxes, trial terms and storage/derived-data rights?

### NSE Data & Analytics
- What products and delivery formats are available for historical order/trade data and real-time tick-by-tick data for NSE CM and F&O?
- Can a retail research workstation obtain a trial/sample? What are the eligibility, connectivity, licensing, redistribution and storage conditions?
- Is aggressor side explicitly present, or must it be reconstructed from order/trade events?

## Sample-data acceptance test

Do not integrate a provider based on a sales statement alone. Obtain a small authorised sample and verify:

- Schema and field definitions match the documentation.
- Records are ordered and timestamp precision/timezone are clear.
- Individual trade prints can be distinguished from quote updates and aggregated ticks.
- Trade quantity sums reconcile plausibly with the corresponding bar/session volume.
- Aggressor-side values exist and the methodology is documented; quantify unknown/unclassified volume.
- For footprint, aggregate buy/sell volume by price and bar and compare a small selected window with the provider's own chart.
- Reconnects, duplicate events, sequence gaps, stale quotes and session resets can be detected.
- Historical and live records use compatible schemas and instrument identifiers.

## Decision

**No purchase or integration yet.** First complete the Monday 23 November 2026 Angel One live-depth operational validation. In parallel, request written answers and sample records from GoCharting, Accelpix and Global Datafeeds. Compare the samples against the acceptance test and the existing ₹2k–₹5k/month budget. If commercial vendor data cannot provide documented trade-side data, investigate an NSE Data & Analytics trial or licensed feed route.

Until a source passes, IADEW must label CVD/footprint as unavailable from its own data pipeline. Keep GoCharting as an independent visual confirmation tool and Angel One Depth20 as snapshot-based liquidity context only.
