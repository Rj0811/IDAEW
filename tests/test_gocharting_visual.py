from pathlib import Path

from src.iadew.gocharting_capture_manager import (
    image_quality,
    safe_name,
    ticker_for,
    validate_capture,
)


def test_ticker_mapping():
    assert ticker_for("NIFTY", "index") == "NSE:NIFTY-I"
    assert ticker_for("BANKNIFTY", "index") == "NSE:BANKNIFTY-I"
    assert ticker_for("RELIANCE", "stock") == "NSE:RELIANCE"


def test_safe_name():
    assert safe_name("NIFTY 50 / INDEX") == "NIFTY_50_INDEX"


def test_validator_rejects_wrong_timeframe_and_unverified_chart_type():
    accepted, errors, checks = validate_capture(
        "NIFTY",
        "https://gocharting.com/terminal?ticker=NSE:NIFTY-I",
        "NSE:NIFTY-I",
        "NSE:NIFTY-I 30m",
        {"visual_content_ok": True},
    )
    assert not accepted
    assert any("5-minute" in error for error in errors)
    assert any("chart type" in error for error in errors)


def test_validator_accepts_only_when_identity_timeframe_and_style_visible():
    accepted, errors, checks = validate_capture(
        "NIFTY",
        "https://gocharting.com/terminal?ticker=NSE:NIFTY-I",
        "NSE:NIFTY-I",
        "NSE:NIFTY-I 5m Footprint",
        {"visual_content_ok": True},
    )
    assert accepted
    assert errors == []
    assert checks["chart_type_confirmed"]


def test_validator_rejects_wrong_symbol():
    accepted, errors, _ = validate_capture(
        "NIFTY",
        "https://gocharting.com/terminal?ticker=NSE:RELIANCE",
        "NSE:RELIANCE",
        "RELIANCE 5m Footprint",
        {"visual_content_ok": True},
    )
    assert not accepted
    assert any("instrument" in error for error in errors)
