# GoCharting visual intelligence POC

## What v1 does

- Opens GoCharting in a dedicated, persistent Chromium profile.
- Leaves login, instrument search, and chart/layout selection under the user's control.
- Captures the visible browser viewport for both index and stock instruments.
- Saves a PNG, JSON metadata sidecar, and the visual-analysis prompt under
  `data/gocharting_captures/`.
- Optionally sends the screenshot to the OpenAI Responses API for a constrained
  visual assessment when `OPENAI_API_KEY` is configured.

The default capture universe is NIFTY, BANKNIFTY, and the symbols in
`CASH_WATCHLIST`. The requested chart interval is 5 minutes. Before each
capture, the user confirms that the correct symbol and 5-minute footprint layout
are visible. This human-in-the-loop step avoids relying on undocumented GoCharting
UI selectors that may change.

## Install (Windows PowerShell)

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

Capture default indices + configured stocks:

```powershell
python run_gocharting_visual.py
```

Capture a smaller first test:

```powershell
python run_gocharting_visual.py --symbols NIFTY BANKNIFTY RELIANCE
```

Stocks or indices only:

```powershell
python run_gocharting_visual.py --stocks-only
python run_gocharting_visual.py --indices-only
```

Optional API-based vision analysis:

```powershell
$env:OPENAI_API_KEY = "your-key-in-local-terminal"
python run_gocharting_visual.py --symbols NIFTY RELIANCE --analyze
```

The API key is read from the process environment and is never written to capture
metadata. API usage is billed separately under the API account; a ChatGPT plan
does not automatically provide API credits. The default model can be changed with
`--model` or `IADEW_VISION_MODEL`.

## Workflow

1. Start the capture command. A dedicated Chromium profile opens at GoCharting.
2. Sign in yourself if required. The profile is local at
   `data/gocharting_browser_profile/`; it is excluded from Git.
3. Set the requested instrument and 5-minute footprint/order-flow layout.
4. Press ENTER in the terminal to capture. Repeat for the next instrument.
5. Review the PNG and metadata in `data/gocharting_captures/`.
6. Without `--analyze`, upload the PNG to ChatGPT and use the companion
   `*_vision_prompt.txt`. With `--analyze`, read the companion analysis Markdown.

## What the model may and may not claim

The visual assistant reports only what is legible in the screenshot. It can
describe visible imbalances, possible absorption locations, price context,
visible CVD/delta labels and important chart levels. It must mark unreadable
values as unknown and state uncertainty.

A screenshot is not a trade-by-trade feed. It cannot establish the sequence of
executions, true exchange aggressor flags, order-book additions/cancellations,
causality, or confirmed absorption. An apparent imbalance/absorption is a visual
candidate requiring independent validation. This module is observation-only:
it does not produce orders, position sizes, or autonomous trade entries.

## Browser and security boundaries

- Uses Playwright to launch a separate local Chromium profile; it does not attach
  to or control the user's everyday Chrome profile.
- User performs login and chart selection. Do not store passwords, cookies, OTPs,
  or broker tokens in IADEW files.
- No GoCharting private endpoints, DOM scraping of market data, or network
  reverse-engineering is used. Only the rendered viewport is captured.
- Respect GoCharting's current terms, subscription permissions, and applicable
  market-data licensing.
