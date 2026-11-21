# GoCharting automated capture manager

## What the current capture manager does

- Launches a dedicated persistent Chromium profile and reuses its GoCharting login.
- Uses the configured watchlist: NIFTY, BANKNIFTY and `CASH_WATCHLIST`.
- Asks for one initial operator confirmation after the user has signed in and configured a 5-minute footprint chart. It does not ask for ENTER between instruments.
- Rotates through symbols using GoCharting's visible terminal URL pattern.
- Captures one high-resolution viewport image per instrument (1920 × 1200 CSS pixels).
- Checks instrument identity, visible 5-minute timeframe, image dimensions and basic visual content before analysis.
- Rejects captures that fail validation; rejected images are never sent to NVIDIA.
- Writes per-image JSON metadata, SHA-256 hashes and a session manifest.

## Important validation boundary

GoCharting renders much of the chart into a canvas. Browser-accessible text does not always expose the selected chart style. The validator therefore fails closed unless it can find a footprint/cluster/bid-ask marker in accessible page text. It does not pretend that a colorful screenshot alone proves the chart is a footprint. If your GoCharting layout does not expose chart type as accessible text, captures will be rejected with a chart-type validation error. Do not bypass this by assuming the screenshot is correct; we should add a platform-specific, independently verified selector after inspecting the actual UI on your machine.

The pixel check is a coarse image-integrity/readability gate, not OCR and not a footprint classifier. A capture accepted by this POC confirms the requested instrument/timeframe and visual-content checks; it does not verify individual footprint values.

## Install (Windows PowerShell)

```powershell
git pull origin main
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

Start automated watchlist capture and send only accepted screenshots to NVIDIA:

```powershell
python run_gocharting_visual.py --analyze
```

Test a smaller set first:

```powershell
python run_gocharting_visual.py --symbols NIFTY BANKNIFTY RELIANCE --analyze
```

Capture only, without AI analysis:

```powershell
python run_gocharting_visual.py --symbols NIFTY BANKNIFTY RELIANCE
```

## One-time session setup

1. Run the command. The dedicated Chromium profile opens GoCharting.
2. Sign in if needed.
3. Configure the 5-minute footprint chart layout once. Keep that layout active.
4. At the terminal prompt, type `YES` to confirm that the visible chart is a 5-minute footprint. This one-time operator confirmation is recorded in every session capture; it replaces the inaccessible canvas chart-type label.

5. The manager navigates each requested instrument, captures one screenshot and validates it before moving on.
6. Inspect `data/gocharting_captures/*_*.json` and the session `capture_manifest_*.json`. Rejected captures include explicit validation errors.

The browser is visible by default. Do not use headless mode for chart capture because chart rendering can differ.

## Current limitations / next hardening step

- UI navigation and the terminal URL pattern can change; no private GoCharting API or network scraping is used.
- The chart style may be canvas-only and inaccessible to browser text inspection. The manager therefore requires one explicit operator confirmation per session that the initial chart is a 5-minute footprint. Instrument, timeframe and image checks still run independently on every capture. This does not prove the chart type remains unchanged after each navigation; it records the operator-confirmed session layout assumption.
- Automatic zoom manipulation is intentionally not enabled yet. The manager uses a large viewport at normal browser zoom rather than zooming out and making footprint cells unreadable.
- This version captures a single viewport image per instrument, as requested. If a full-session overview and readable cells cannot both fit, a later multi-region mode will be more appropriate.
- NVIDIA inference can still time out or exhaust its token budget; those failures are recorded separately from capture validation.

## Safety and data limitations

A screenshot is a visual snapshot, not a trade-by-trade feed. It cannot establish true exchange aggressor flags, execution sequence, order-book additions/cancellations, causality or confirmed absorption. The module is observation-only and never places broker orders. Keep credentials in local `.env`; never commit API keys, cookies, OTPs or broker tokens.
