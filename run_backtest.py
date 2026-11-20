"""Run 90-trading-session historical replay and paper backtest.

Examples:
    python run_backtest.py
    python run_backtest.py --days 90 --timeframe FIVE_MINUTE --style both
    python run_backtest.py --days 90 --style intraday
"""
import argparse
from src.iadew.backtest import run_historical_backtest


def main():
    parser = argparse.ArgumentParser(description="IADEW historical replay and paper backtest")
    parser.add_argument("--days", type=int, default=90, help="Number of trading sessions to replay")
    parser.add_argument("--timeframe", choices=["FIVE_MINUTE"], default="FIVE_MINUTE")
    parser.add_argument("--style", choices=["both", "intraday", "swing"], default="both")
    parser.add_argument("--capital", type=float, default=500000)
    parser.add_argument("--risk-pct", type=float, default=0.005)
    parser.add_argument("--cost-bps", type=float, default=3.0, help="Estimated cost per side in basis points")
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    args = parser.parse_args()
    styles = ("intraday", "swing") if args.style == "both" else (args.style,)
    run_id, result = run_historical_backtest(
        days=args.days, timeframe=args.timeframe, styles=styles,
        capital=args.capital, risk_pct=args.risk_pct,
        cost_bps_per_side=args.cost_bps, slippage_bps=args.slippage_bps,
    )
    print(f"Backtest run: {run_id}")
    for key, value in result.items():
        print(f"{key}: {value}")
    print("Results saved to data/iadew.sqlite3; open Streamlit dashboard to review.")


if __name__ == "__main__":
    main()
