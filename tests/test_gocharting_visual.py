from pathlib import Path
from src.iadew.gocharting_visual import build_record, safe_name


def test_safe_name():
    assert safe_name("NIFTY 50 / INDEX") == "NIFTY_50_INDEX"


def test_build_record_marks_snapshot_limitations(tmp_path):
    image = Path("data/gocharting_captures/test.png")
    record = build_record("nifty", "index", image, "https://gocharting.com/", "Chart")
    assert record["instrument"] == "NIFTY"
    assert record["timeframe_requested"] == "5m"
    assert record["analysis_status"] == "pending"
    assert any("not a complete" in item for item in record["limitations"])
