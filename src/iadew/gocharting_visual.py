"""GoCharting browser screenshot collector for IADEW.

Uses a dedicated persistent Chromium profile. The user signs in and selects each
instrument/chart manually; IADEW only captures the rendered page and does not
inspect private network traffic or automate trading.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[2]
IST = ZoneInfo("Asia/Kolkata")
CAPTURE_DIR = ROOT / "data" / "gocharting_captures"
PROFILE_DIR = ROOT / "data" / "gocharting_browser_profile"

VISION_PROMPT = """You are IADEW's visual market-structure assistant. Inspect this GoCharting
chart screenshot, treating it as visual evidence only. The requested chart timeframe
is 5 minutes. Extract only legible information and explicitly mark unreadable or
not-visible values as unknown. Do not invent numeric delta, CVD, prices, volume,
footprint cells, or order-flow values.

Return concise JSON with these keys:
instrument_visible, timeframe_visible, chart_type_visible, price_context,
footprint_observations, imbalance_candidates, absorption_candidates,
initiative_or_failed_auction, cvd_or_delta_observation, key_levels_visible,
bullish_evidence, bearish_evidence, missing_or_unreadable, confidence
(0-1), caveats, conclusion.
Distinguish a visible footprint imbalance from proof of aggressor-side executions.
A screenshot cannot establish sequence, causality, queue changes, or confirmed
absorption. This is research commentary, not a trade instruction. Never output
a buy/sell order or position size."""


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip().upper()).strip("._-")
    return cleaned[:48] or "UNKNOWN"


def build_record(instrument: str, asset_class: str, image_path: Path,
                 page_url: str, title: str) -> dict:
    now = datetime.now(IST)
    return {
        "captured_at_ist": now.isoformat(timespec="seconds"),
        "instrument": instrument.strip().upper(),
        "asset_class": asset_class,
        "timeframe_requested": "5m",
        "source": "GoCharting rendered browser page",
        "page_url": page_url,
        "page_title": title,
        "image_path": str(image_path.relative_to(ROOT)),
        "analysis_status": "pending",
        "limitations": [
            "Screenshot is a visual snapshot, not a complete trade/order event feed.",
            "Only values legible in the captured viewport can be assessed.",
            "No trade execution or broker order routing is performed."
        ]
    }


def analyze_with_openai(image_path: Path, model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured; use the saved screenshot with ChatGPT manually.")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": VISION_PROMPT},
                {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}", "detail": "high"}
            ]
        }]
    }
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload, timeout=120
    )
    response.raise_for_status()
    body = response.json()
    texts = []
    for item in body.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                texts.append(part.get("text", ""))
    if not texts:
        raise RuntimeError(f"No text returned by vision model: {json.dumps(body)[:1200]}")
    return "\n".join(texts)


def capture_session(instruments: list[tuple[str, str]], headless: bool = False,
                    analyze: bool = False, model: str = "gpt-4.1-mini") -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install browser dependency: pip install playwright; then run playwright install chromium") from exc

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1600, "height": 1000},
            accept_downloads=False
        )
        page = context.pages[0] if context.pages else context.new_page()
        if "gocharting.com" not in (page.url or ""):
            page.goto("https://gocharting.com/", wait_until="domcontentloaded", timeout=60000)
        print("\nGoCharting browser opened. Sign in if needed. Keep the chart in a 5-minute")
        print("footprint/order-flow layout. IADEW does not read credentials or private APIs.\n")

        for index, (instrument, asset_class) in enumerate(instruments, start=1):
            print(f"[{index}/{len(instruments)}] Prepare {instrument} ({asset_class}) in GoCharting.")
            print("Select the instrument and confirm the visible chart timeframe is 5 minutes.")
            input("Press ENTER to capture this chart (Ctrl+C to stop): ")
            page.wait_for_timeout(1200)
            stamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
            stem = f"{stamp}_{safe_name(instrument)}_5m"
            image_path = CAPTURE_DIR / f"{stem}.png"
            page.screenshot(path=str(image_path), full_page=False)
            record = build_record(instrument, asset_class, image_path, page.url, page.title())
            if analyze:
                try:
                    result = analyze_with_openai(image_path, model)
                    analysis_path = CAPTURE_DIR / f"{stem}_analysis.md"
                    analysis_path.write_text(result, encoding="utf-8")
                    record["analysis_status"] = "completed"
                    record["analysis_path"] = str(analysis_path.relative_to(ROOT))
                except Exception as exc:
                    record["analysis_status"] = "failed"
                    record["analysis_error"] = str(exc)
                    print(f"Vision analysis failed: {exc}")
            metadata_path = CAPTURE_DIR / f"{stem}.json"
            metadata_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            prompt_path = CAPTURE_DIR / f"{stem}_vision_prompt.txt"
            prompt_path.write_text(VISION_PROMPT, encoding="utf-8")
            print(f"Saved: {image_path}")
            print(f"Metadata: {metadata_path}")
            if not analyze:
                print("Vision step: upload the PNG to ChatGPT and paste the companion prompt.")
        context.close()


def default_universe() -> list[tuple[str, str]]:
    stocks = [s.strip().upper() for s in os.getenv(
        "CASH_WATCHLIST", "RELIANCE,HDFCBANK,ICICIBANK,SBIN,INFY,TCS,ITC,LT,AXISBANK,BAJFINANCE"
    ).split(",") if s.strip()]
    return [("NIFTY", "index"), ("BANKNIFTY", "index")] + [(s, "stock") for s in stocks]


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture GoCharting 5-minute charts for IADEW visual review.")
    parser.add_argument("--symbols", nargs="*", help="Override default NIFTY, BANKNIFTY and CASH_WATCHLIST universe.")
    parser.add_argument("--stocks-only", action="store_true")
    parser.add_argument("--indices-only", action="store_true")
    parser.add_argument("--analyze", action="store_true", help="Analyze each screenshot with OpenAI API (requires OPENAI_API_KEY).")
    parser.add_argument("--model", default=os.getenv("IADEW_VISION_MODEL", "gpt-4.1-mini"))
    args = parser.parse_args()

    universe = default_universe()
    if args.symbols:
        universe = [(s.upper(), "index" if s.upper() in {"NIFTY", "BANKNIFTY"} else "stock") for s in args.symbols]
    if args.stocks_only:
        universe = [(s, c) for s, c in universe if c == "stock"]
    if args.indices_only:
        universe = [(s, c) for s, c in universe if c == "index"]
    if not universe:
        parser.error("No instruments selected.")
    capture_session(universe, analyze=args.analyze, model=args.model)


if __name__ == "__main__":
    main()
