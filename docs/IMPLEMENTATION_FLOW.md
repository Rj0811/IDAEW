# End-to-end implementation flow

Start workstation -> authenticate Kite -> refresh instrument master -> load historical candles -> validate timestamps/OHLCV -> build features -> apply universe filters -> rank candidates -> apply data and risk gates.

If a gate fails, suppress the alert and log the reason. If all gates pass, publish a candidate alert. Open the chart in GoCharting and inspect footprint/DOM using the provider's documented features. The trader approves or rejects the setup. Approved trades are placed manually in Kite, then fills, stops, exits and costs are recorded for review.

## Alert lifecycle
DETECTED -> QUALIFIED -> ALERTED -> HUMAN_REVIEW -> APPROVED/REJECTED -> EXECUTED -> CLOSED -> REVIEWED

Alerts expire when the trigger is invalidated, data becomes stale, the setup window passes, or the instrument/contract changes. Duplicate alerts for the same instrument/setup/zone are suppressed for a configurable cooldown.

## Flow diagram
A[Start] -> B[Authenticate Kite]
B -> C[Refresh instruments]
C -> D[Load and validate market data]
D -> E[Calculate features]
E -> F[Scan and rank]
F -> G{Risk and data gates pass?}
G ->|No| H[Suppress and log]
G ->|Yes| I[Publish alert]
I -> J[Human chart review]
J -> K{Trader approves?}
K ->|No| L[Journal rejection]
K ->|Yes| M[Manual broker execution]
M -> N[Record fills and costs]
N -> O[Performance review]
