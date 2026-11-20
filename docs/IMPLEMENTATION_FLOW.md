# End-to-end implementation flow

Start workstation -> authenticate Angel One SmartAPI with TOTP -> refresh/cache Angel One scrip master -> resolve NSE/NFO symbol tokens -> load historical candles -> validate timestamps/OHLCV -> build features -> apply universe filters -> rank candidates -> apply data and risk gates.

The live-data path subscribes to Angel One SmartAPI WebSocket V2 using the matching exchange type and token. Normalize decoded quote packets and validate feed freshness before using them in live features.

If a gate fails, suppress the alert and log the reason. If all gates pass, publish a candidate alert. Open the chart in GoCharting and inspect footprint/DOM using the provider's documented features. The trader approves or rejects the setup. Approved trades are placed manually in Angel One, then fills, stops, exits and costs are recorded for review.

## Alert lifecycle
DETECTED -> QUALIFIED -> ALERTED -> HUMAN_REVIEW -> APPROVED/REJECTED -> EXECUTED -> CLOSED -> REVIEWED

Alerts expire when the trigger is invalidated, data becomes stale, the setup window passes, or the instrument/contract changes. Duplicate alerts for the same instrument/setup/zone are suppressed for a configurable cooldown.

## Flow diagram
A[Start] -> B[Authenticate Angel One SmartAPI]
B -> C[Refresh scrip master and resolve tokens]
C -> D[Load and validate historical candles]
D -> E[Subscribe WebSocket V2]
E -> F[Calculate features]
F -> G[Scan and rank]
G -> H{Risk and data gates pass?}
H ->|No| I[Suppress and log]
H ->|Yes| J[Publish alert]
J -> K[Human chart review]
K -> L{Trader approves?}
L ->|No| M[Journal rejection]
L ->|Yes| N[Manual execution in Angel One]
N -> O[Record fills and costs]
O -> P[Performance review]
