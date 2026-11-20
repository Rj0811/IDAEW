"""Evaluate snapshot depth imbalance against subsequent 1m/5m price movement.

This is descriptive research only. Candle-close matching is approximate and
does not establish executable returns or causality.
"""
import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.iadew.config import settings
from src.iadew.depth_analytics import depth_metrics


def _parse_time(value):
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("Asia/Kolkata")
    return stamp


def load_samples(days):
    if not settings.db_path.exists():
        raise RuntimeError(f"Database not found: {settings.db_path}")
    cutoff = (pd.Timestamp.now(tz="Asia/Kolkata") - pd.Timedelta(days=days)).isoformat()
    with sqlite3.connect(settings.db_path, timeout=20) as con:
        snapshots = pd.read_sql_query(
            """SELECT token, received_timestamp, buy_levels_json, sell_levels_json
               FROM depth_snapshots WHERE received_timestamp >= ?
               ORDER BY token, received_timestamp""", con, params=(cutoff,))
        bars = pd.read_sql_query(
            """SELECT token, bar_time, close FROM live_bars
               WHERE timeframe='1m' ORDER BY token, bar_time""", con)
    if snapshots.empty or bars.empty:
        raise RuntimeError("Need both depth_snapshots and matching 1m live_bars. Run: python run_live_feed.py --depth")
    snapshots["time"] = snapshots["received_timestamp"].map(_parse_time)
    bars["time"] = bars["bar_time"].map(_parse_time)
    bars["close"] = pd.to_numeric(bars["close"], errors="coerce")
    samples = []
    for token, group in snapshots.groupby("token"):
        price_rows = bars[bars.token.astype(str) == str(token)].dropna(subset=["close"]).sort_values("time")
        if price_rows.empty:
            continue
        price_times = price_rows["time"].tolist()
        prices = price_rows["close"].astype(float).tolist()
        for row in group.itertuples(index=False):
            metrics = depth_metrics(
                __import__("json").loads(row.buy_levels_json),
                __import__("json").loads(row.sell_levels_json))
            if metrics["best_bid"] is None:
                continue
            signal_time = row.time
            # Use the first candle timestamp at/after the snapshot as the
            # baseline, then the first candle at/after each forward horizon.
            base_idx = next((i for i, t in enumerate(price_times) if t >= signal_time), None)
            if base_idx is None:
                continue
            record = {
                "token": str(token), "snapshot_time": signal_time.isoformat(),
                "imbalance_5": metrics["imbalance_5"],
                "imbalance_10": metrics["imbalance_10"],
                "imbalance_20": metrics["imbalance_20"],
                "divergence": (
                    "near_bid_deep_ask" if metrics["imbalance_5"] >= 15 and metrics["imbalance_20"] <= -10 else
                    "near_ask_deep_bid" if metrics["imbalance_5"] <= -15 and metrics["imbalance_20"] >= 10 else
                    "none"
                ),
            }
            for horizon in (1, 5):
                target_time = signal_time + pd.Timedelta(minutes=horizon)
                target_idx = next((i for i, t in enumerate(price_times) if t >= target_time), None)
                if target_idx is not None and target_idx > base_idx and prices[base_idx] > 0:
                    record[f"return_{horizon}m_pct"] = (
                        prices[target_idx] / prices[base_idx] - 1.0) * 100.0
                else:
                    record[f"return_{horizon}m_pct"] = None
            samples.append(record)
    return pd.DataFrame(samples)


def summarize(frame):
    if frame.empty:
        return pd.DataFrame()
    rows = []
    for feature in ("imbalance_5", "imbalance_10", "imbalance_20"):
        labels = [-100.001, -15, 15, 100.001]
        names = ["Ask-heavy (< -15%)", "Balanced (-15% to +15%)", "Bid-heavy (> +15%)"]
        grouped = pd.cut(frame[feature], bins=labels, labels=names, include_lowest=True)
        for bucket, subset in frame.groupby(grouped, observed=False):
            for horizon in (1, 5):
                values = pd.to_numeric(subset[f"return_{horizon}m_pct"], errors="coerce").dropna()
                rows.append({
                    "feature": feature, "bucket": str(bucket), "horizon": f"{horizon}m",
                    "samples": int(values.count()),
                    "mean_return_pct": round(float(values.mean()), 5) if len(values) else None,
                    "median_return_pct": round(float(values.median()), 5) if len(values) else None,
                    "positive_return_pct": round(float((values > 0).mean() * 100), 2) if len(values) else None,
                })
    for label, subset in frame.groupby("divergence"):
        for horizon in (1, 5):
            values = pd.to_numeric(subset[f"return_{horizon}m_pct"], errors="coerce").dropna()
            rows.append({
                "feature": "divergence", "bucket": label, "horizon": f"{horizon}m",
                "samples": int(values.count()),
                "mean_return_pct": round(float(values.mean()), 5) if len(values) else None,
                "median_return_pct": round(float(values.median()), 5) if len(values) else None,
                "positive_return_pct": round(float((values > 0).mean() * 100), 2) if len(values) else None,
            })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Validate depth imbalance vs subsequent price movement")
    parser.add_argument("--days", type=int, default=5, help="Calendar lookback, default 5")
    args = parser.parse_args()
    samples = load_samples(max(1, args.days))
    summary = summarize(samples)
    if samples.empty:
        raise SystemExit("No matched depth snapshots and 1m candles found for the selected period.")
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sample_path = out_dir / f"depth_validation_samples_{stamp}.csv"
    summary_path = out_dir / f"depth_validation_summary_{stamp}.csv"
    samples.to_csv(sample_path, index=False)
    summary.to_csv(summary_path, index=False)
    print(f"Matched snapshots: {len(samples):,}")
    print(f"Samples with 1m returns: {samples['return_1m_pct'].notna().sum():,}")
    print(f"Samples with 5m returns: {samples['return_5m_pct'].notna().sum():,}")
    print("\nSummary by imbalance bucket and horizon:")
    print(summary.to_string(index=False))
    print(f"\nSaved observations: {sample_path}")
    print(f"Saved summary: {summary_path}")
    print("Research only: candle matching is approximate; no fees, spread, slippage or executable fills are modeled.")


if __name__ == "__main__":
    main()
