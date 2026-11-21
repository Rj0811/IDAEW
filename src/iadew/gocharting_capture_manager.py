"""Automated GoCharting capture manager.

Automates watchlist rotation using the public terminal URL and visible UI.
The user signs in and configures a 5-minute footprint chart once per session.
Each symbol capture is independently checked before it can be sent to vision.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

IST = ZoneInfo("Asia/Kolkata")
ROOT = Path(__file__).resolve().parents[2]
CAPTURE_DIR = ROOT / "data" / "gocharting_captures"
PROFILE_DIR = ROOT / "data" / "gocharting_browser_profile"
BASE_URL = "https://gocharting.com/terminal?ticker="

VISION_PROMPT = """IADEW visual extraction. Inspect this verified 5-minute footprint screenshot.
Read only clearly visible values; use unknown otherwise. Do not infer missing values.
Return compact JSON: instrument, visible_timeframe, chart_type, last_visible_price,
visible_ohlc, visible_key_levels, footprint_visible, visible_imbalance,
possible_absorption, visible_delta_or_cvd, bullish_evidence, bearish_evidence,
unreadable_items, confidence_0_to_1, caveats.
A screenshot cannot prove aggressor-side executions, event sequence, or absorption.
Research only; never provide orders, position sizes, or trade instructions."""


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip().upper()).strip("._-")[:48] or "UNKNOWN"


def ticker_for(symbol: str, asset_class: str) -> str:
    """Map watchlist symbols to GoCharting NSE ticker notation."""
    if symbol.upper() == "NIFTY":
        return "NSE:NIFTY-I"
    if symbol.upper() == "BANKNIFTY":
        return "NSE:BANKNIFTY-I"
    return f"NSE:{symbol.upper()}"


def image_quality(path: Path) -> dict:
    """Independent coarse pixel check; not an order-flow classifier."""
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        width, height = rgb.size
        # Ignore browser chrome and sidebars; sample the central chart viewport.
        crop = rgb.crop((int(width * .04), int(height * .08), int(width * .94), int(height * .91)))
        pixels = list(crop.resize((240, 140)).getdata())
    colorful = sum(1 for r, g, b in pixels if max(r, g, b) - min(r, g, b) > 55 and max(r, g, b) > 90)
    non_dark = sum(1 for r, g, b in pixels if max(r, g, b) > 55)
    return {
        "width": width, "height": height,
        "colorful_pixel_ratio": round(colorful / max(1, len(pixels)), 4),
        "non_dark_pixel_ratio": round(non_dark / max(1, len(pixels)), 4),
        "visual_content_ok": width >= 1400 and height >= 800 and non_dark / max(1, len(pixels)) >= .025,
    }


def validate_capture(symbol: str, page_url: str, page_title: str, visible_text: str,
                     quality: dict) -> tuple[bool, list[str], dict]:
    """Fail-closed identity/timeframe/content checks independent of GLM."""
    problems = []
    expected = ticker_for(symbol, "index" if symbol in {"NIFTY", "BANKNIFTY"} else "stock")
    url_and_title = f"{page_url} {page_title}".upper()
    visible = visible_text.upper()
    aliases = [expected.upper(), symbol.upper()]
    if not any(alias in url_and_title for alias in aliases):
        problems.append("requested instrument not confirmed by page URL/title")
    # The timeframe must be visible in page text; don't assume the URL's request means it applied.
    if not re.search(r"(?<![A-Z0-9])5M(?![A-Z0-9])", visible):
        problems.append("5-minute timeframe not confirmed in visible page text")
    if not quality.get("visual_content_ok"):
        problems.append("screenshot dimensions/content check failed")
    # GoCharting canvas may not expose chart style in accessible text. Never claim
    # footprint validation based only on colorful pixels; require explicit opt-in.
    style_confirmed = bool(re.search(r"FOOTPRINT|CLUSTER|BID.?ASK", visible))
    if not style_confirmed:
        problems.append("footprint chart type not independently confirmed in accessible page text")
    return not problems, problems, {
        "instrument_confirmed": not any("instrument" in p for p in problems),
        "timeframe_confirmed": not any("timeframe" in p for p in problems),
        "chart_type_confirmed": style_confirmed,
        "visual_content_ok": bool(quality.get("visual_content_ok")),
    }


def build_record(instrument: str, asset_class: str, image_path: Path,
                 page_url: str, title: str) -> dict:
    return {
        "captured_at_ist": datetime.now(IST).isoformat(timespec="seconds"),
        "instrument": instrument.upper(), "asset_class": asset_class,
        "timeframe_requested": "5m", "source": "GoCharting rendered browser page",
        "page_url": page_url, "page_title": title,
        "image_path": str(image_path.relative_to(ROOT)),
        "analysis_status": "pending",
        "limitations": [
            "Screenshot is a visual snapshot, not a complete trade/order event feed.",
            "Only values legible in the captured viewport can be assessed.",
            "No trade execution or broker order routing is performed."
        ]
    }


def analyze_with_nvidia(image_path: Path, model: str) -> str:
    from .nvidia_client import analyze_image_with_nvidia
    return analyze_image_with_nvidia(
        image_path=image_path, prompt=VISION_PROMPT, model=model,
        max_tokens=8192, temperature=0.3,
    )


def capture_session(instruments: list[tuple[str, str]], headless: bool = False,
                    analyze: bool = False, model: str = "z-ai/glm-5.3-flash",
                    auto: bool = True) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install Playwright: pip install playwright; python -m playwright install chromium") from exc

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=headless,
            viewport={"width": 1920, "height": 1200}, device_scale_factor=1,
            accept_downloads=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(BASE_URL + "NSE:NIFTY-I", wait_until="domcontentloaded", timeout=60000)
        print("\nSign in if required. Configure a 5-minute footprint chart ONCE.")
        print("Keep the footprint layout active; the collector will rotate symbols.")
        print("Press ENTER once when the initial chart is ready (not once per symbol).")
        input("Ready to start automated watchlist capture? ")
        for index, (instrument, asset_class) in enumerate(instruments, start=1):
            ticker = ticker_for(instrument, asset_class)
            page.goto(BASE_URL + ticker, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(3500)
            # Reassert 5m using the visible toolbar when an unambiguous visible control exists.
            five_minute = page.get_by_text("5m", exact=True).filter(visible=True)
            try:
                if five_minute.count() == 1:
                    five_minute.click(timeout=2500)
                    page.wait_for_timeout(1200)
            except Exception:
                pass
            stamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
            stem = f"{stamp}_{safe_name(instrument)}_5m"
            image_path = CAPTURE_DIR / f"{stem}.png"
            page.screenshot(path=str(image_path), full_page=False, animations="disabled")
            visible_text = page.locator("body").inner_text(timeout=5000)
            quality = image_quality(image_path)
            accepted, problems, checks = validate_capture(
                instrument.upper(), page.url, page.title(), visible_text, quality
            )
            record = build_record(instrument, asset_class, image_path, page.url, page.title())
            record.update({
                "capture_status": "accepted" if accepted else "rejected",
                "validation": checks, "validation_errors": problems,
                "image_quality": quality,
                "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "capture_sequence": index,
                "capture_mode": "single",
            })
            if accepted and analyze:
                try:
                    result = analyze_with_nvidia(image_path, model)
                    analysis_path = CAPTURE_DIR / f"{stem}_analysis.md"
                    analysis_path.write_text(result, encoding="utf-8")
                    record["analysis_status"] = "completed"
                    record["analysis_path"] = str(analysis_path.relative_to(ROOT))
                except Exception as exc:
                    record["analysis_status"] = "failed"
                    record["analysis_error"] = str(exc)
            elif not accepted:
                record["analysis_status"] = "skipped_validation_failed"
            metadata_path = CAPTURE_DIR / f"{stem}.json"
            metadata_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            manifest.append({"instrument": instrument, "metadata": str(metadata_path.relative_to(ROOT)),
                             "capture_status": record["capture_status"],
                             "analysis_status": record["analysis_status"],
                             "validation_errors": problems})
            status = "ACCEPTED" if accepted else "REJECTED"
            print(f"[{index}/{len(instruments)}] {instrument}: {status}")
            for problem in problems:
                print(f"  - {problem}")
            if accepted and not analyze:
                print(f"  Saved {image_path}; run again with --analyze to send validated captures to GLM.")
        manifest_path = CAPTURE_DIR / f"capture_manifest_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nCapture manifest: {manifest_path}")
        context.close()


def default_universe() -> list[tuple[str, str]]:
    from .config import settings
    return [("NIFTY", "index"), ("BANKNIFTY", "index")] + [(s, "stock") for s in settings.watchlist]


def main() -> None:
    import argparse
    import os
    parser = argparse.ArgumentParser(description="Automated GoCharting single-image watchlist capture and validation.")
    parser.add_argument("--symbols", nargs="*", help="Override default NIFTY, BANKNIFTY and configured cash watchlist.")
    parser.add_argument("--stocks-only", action="store_true")
    parser.add_argument("--indices-only", action="store_true")
    parser.add_argument("--analyze", action="store_true", help="Send accepted captures to NVIDIA NIM.")
    parser.add_argument("--model", default=os.getenv("NVIDIA_MODEL", "z-ai/glm-5.3-flash"))
    parser.add_argument("--headless", action="store_true", help="Not recommended: chart rendering may require a visible browser.")
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
    capture_session(universe, headless=args.headless, analyze=args.analyze, model=args.model)


if __name__ == "__main__":
    main()
