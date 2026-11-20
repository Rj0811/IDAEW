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
| GoCharting | Bar Statistics documents per-bar trades, buy/sell trades, volume and buy/sell volume, delta, cumulative delta and POC. Delta docs define buy volume as volume traded at offer and sell volume at bid. Layout docs list an Excel Download control and Bar Replay. | Public docs do not specify the Excel export schema, whether it includes price-level footprint rows, whether historical/replayed order-flow metrics export, or any supported API for extracting the underlying data. The documented classification is quote/offer-bid based; no India-specific feed methodology is stated on these pages. | Best immediate route to investigate because the user already subscribes. Test the documented Excel Download against a footprint chart; no integration until export fields and permissions are confirmed. |
| Accelpix | Live Trade callback sample has ticker, segmentId, timestamp, price, qty, cumulative volume and OI. Best callback separately provides best bid/ask prices and quantities. Historical `get_back_ticks` sample has timestamp, price, volume and OI; intra-day history is minute bars. | The sample Trade schema has no aggressor-side field and no bid/ask-at-trade fields. Best quote is a separate callback. The historical tick sample is not shown with side classification or order-book events. Historical retention, exact tick semantics, sequencing, depth history, commercial terms and prices are not specified on the inspected page. | Promising for live trade prints, but NOT yet a CVD-ready feed from documented schema. Ask if side classification or exchange order/trade messages are available; otherwise it may support prints plus quote-based classification only if timestamp/sequence quality is sufficient. |
| Global Datafeeds | API docs advertise real-time updates at 1-second frequency with L1 best bid/ask. Historical Tick/Minute/EOD API exists. Published NFO tick sample includes BUYPRICE/BUYQTY, SELLPRICE/SELLQTY, LASTTRADEPRICE/LASTTRADETIME, TRADEDQTY and OI. | Tick periodicity is explicitly one second, not individual trade-by-trade. Sample records are time snapshots combining best bid/ask and last-trade fields; no aggressor-side flag or sequence of individual executions is documented. NSE CM tick backfill is stated as one calendar week. | Useful candidate for 1-second quote/trade snapshots and context, but does NOT meet the strict individual-print + aggressor-side requirement as documented. |
| NSE Data & Analytics direct | Official real-time page describes L1 best bid/ask, L2 best 5, L3 best 20 and tick-by-tick full order book. Official historical page offers historical Order & Trade data for CM, F&O, CD and COM; CM includes order and trade level information. | Exact segment/product availability for MTBT, delivery format, access route, pricing, licence and whether aggressor side is explicit vs reconstructable require direct confirmation. The public real-time page describes dedicated leased-line delivery or authorised data vendors. | Strongest documented route for full exchange event/order-trade research. Investigate a sample and commercial feasibility; likely not a low-cost retail API subscription. |

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

## Documentation findings and practical interpretation

### GoCharting
The public Bar Statistics page explicitly documents Buy/Sell trades and Buy/Sell volume at each price level, along with Delta, Cumulative Delta and POC. Its Delta page says delta is volume traded at the offer minus volume traded at the bid. The Layout Setup page documents an Excel Download control and Bar Replay. This is enough to confirm the platform exposes useful order-flow analytics visually, but it does not establish that the Excel download contains raw price-level bid/ask volume or historical footprint records. This is the first thing to test inside the existing paid account.

### Accelpix
The live Trade callback sample contains `id`, `ticker`, `segmentId`, `time`, `price`, `qty`, `volume`, `oi` and `kind`. A separate Best callback contains bid/ask prices and quantities. Historical `get_back_ticks` is documented from a specified date/time up to current live time; its sample contains timestamp, price, volume and OI. The docs also provide minute-level intra-day history. No aggressor-side field is shown in the published Trade or historical tick samples. It is a stronger live-print candidate than Global Datafeeds, but the schema alone does not establish aggressor side or complete sequencing.

### Global Datafeeds
The vendor states real-time data updates at 1-second frequency with L1 best bid/ask. Its historical GetHistory supports TICK/MINUTE/EOD, but its own sample defines TICK as one-second intervals. The published NFO tick response contains best bid/ask price and quantity, last trade price/time, traded quantity and OI; it does not contain buyer/seller aggressor classification or individual execution IDs. NSE CM historical TICK backfill is stated as one calendar week. Treat this as one-second market snapshots, not an individual-trade tape.

### NSE Data & Analytics
The official real-time product page describes Level 1 best bid/ask, Level 2 best five, Level 3 best twenty and tick-by-tick full order-book data. Its historical Order & Trade page lists historical order/trade data for CM, F&O, CD and COM, with CM order and trade-level information. This is the clearest public documentation of the event-level data IADEW ultimately wants, but the delivery route and commercial terms need direct confirmation. The public real-time page describes dedicated leased-line delivery or access through authorised data vendors.

## Questions to send providers

### GoCharting
- The docs list Excel Download and Bar Statistics Buy/Sell Volume at each price level. Does the Excel Download actually export cluster/footprint rows per price level (bid volume, ask volume, total volume, delta), or only chart OHLC/indicator values?
- Can this be exported for historical/replayed bars and expired NIFTY/BANKNIFTY contracts?
- Is there a documented API, file export, or webhook that exposes those numeric records? Please share schema and sample.
- Does the India feed's buy/sell classification represent exchange aggressor side, quote-based classification, or another methodology?
- What are the retention limits and terms for storing exported data and using it in a private research application?

### Accelpix and Global Datafeeds
- For Accelpix, please provide raw live Trade and Best callback samples plus historical get_back_ticks output for NIFTY futures and one liquid NSE stock. Are Trade callback events individual executions with unique IDs and sequence numbers?
- Does each event represent an individual executed trade, a quote update, or a sampled/aggregated tick? For Global Datafeeds, can you explain the documented one-second TICK record and whether any faster individual-trade stream exists?
- Are trade price, trade quantity, exchange timestamp, best bid/ask and aggressor side provided on the same event? If not, what sequence numbers and timestamp precision allow reliable trade/quote matching?
- If aggressor side is derived, provide the exact classification method and handling of locked/crossed/stale quotes and unclassified trades.
- What is the historical tick retention by NSE cash, index futures and stock futures? Can data be retrieved for expired contracts?
- Is historical depth available? Are there sequenced order add/modify/cancel/execute events, or only snapshots?
- What are API limits, simultaneous subscriptions, latency expectations, monthly/annual cost, taxes, trial terms and storage/derived-data rights?

### NSE Data & Analytics
- Please confirm segment-by-segment availability of historical order/trade data and real-time tick-by-tick full order-book data (CM and F&O specifically), including file/message schemas and sample files.
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

**No purchase or integration yet.** Documentation review narrows the sequence:

1. Test GoCharting's Excel Download in the existing subscription. This is the lowest incremental-cost test. Verify whether it exports numeric per-price Buy/Sell Volume and Delta, not just OHLC/indicator columns.
2. Ask Accelpix to confirm whether its live Trade callback is an individual execution tape with sequence/unique IDs and whether it can supply aggressor-side classification. Its published schema has trade-like price/qty events but no side field.
3. Deprioritize Global Datafeeds for true footprint: its documented TICK stream is one-second snapshots, with best bid/ask and last-trade fields, not a documented individual execution tape or aggressor side. It may still be useful as a low-complexity quote/context feed.
4. Request NSE Data & Analytics historical order/trade sample files and confirm F&O real-time event coverage, delivery and commercial terms. This is the most directly relevant documented source, but likely needs a separate budget decision.

Complete the Monday 23 November 2026 Angel One depth operational validation independently. Keep the ₹2k–₹5k/month budget constraint visible; do not assume NSE direct data is affordable or accessible without a quote.

Until a source passes, IADEW must label CVD/footprint as unavailable from its own data pipeline. Keep GoCharting as an independent visual confirmation tool and Angel One Depth20 as snapshot-based liquidity context only.


## Review outcome (21 November 2026)

- [x] Read GoCharting Bar Statistics, Delta/Cumulative Delta and Layout Setup documentation.
- [x] Read Accelpix Python API live Trade/Best callbacks and historical tick documentation.
- [x] Read Global Datafeeds Type of Data, GetHistory and published NFO TICK sample.
- [x] Read NSE Data & Analytics real-time subscription and historical Order & Trade product descriptions.
- [ ] Test GoCharting Excel export from an actual footprint chart and inspect columns/rows.
- [ ] Obtain Accelpix sample and written clarification on event semantics, sequencing and aggressor side.
- [ ] Obtain NSE historical order/trade sample and quote for relevant segments.
- [ ] Revisit provider choice after Monday's Angel One depth test and sample-data review.
