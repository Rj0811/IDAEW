import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src.iadew.config import settings

IST = ZoneInfo("Asia/Kolkata")
DB_PATH = settings.db_path

st.set_page_config(page_title="IADEW", layout="wide")
st.title("IADEW — Institutional Activity Watchlist")
st.caption("Research workstation. Scanner scores are heuristics, not probabilities or proof of institutional participation.")


def table_exists(con, name):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


@st.fragment(run_every="5s")
def live_market_panel():
    st.subheader("Live market monitor")
    if not DB_PATH.exists():
        st.info("Market database not found. Start the collector with: python run_live_feed.py")
        return
    with sqlite3.connect(DB_PATH, timeout=5) as con:
        if not table_exists(con, "live_bars"):
            st.info("Live candle table not initialized. Start: python run_live_feed.py")
            return
        bars = pd.read_sql_query(
            """SELECT token, exchange_type, timeframe, bar_time, open, high, low, close,
                      volume, tick_count FROM live_bars ORDER BY bar_time DESC LIMIT 1000""", con)
    if bars.empty:
        st.warning("No live ticks have been persisted yet.")
        return
    bars["bar_time"] = pd.to_datetime(bars["bar_time"], errors="coerce")
    bars = bars.dropna(subset=["bar_time"])
    if bars.empty:
        st.warning("No valid exchange timestamps in live candle data.")
        return
    latest = bars.sort_values("bar_time").iloc[-1]
    stamp = latest["bar_time"]
    stamp = stamp.tz_localize(IST) if stamp.tzinfo is None else stamp.tz_convert(IST)
    age = max(0, int((datetime.now(IST) - stamp.to_pydatetime()).total_seconds()))
    a, b, c = st.columns(3)
    a.metric("Latest exchange candle", stamp.strftime("%d %b %Y, %H:%M:%S IST"))
    b.metric("Latest close", f"₹{float(latest['close']):,.2f}")
    c.metric("Exchange data age", f"{age // 60}m {age % 60}s")
    timeframe = st.selectbox("Live candle timeframe", ["1m", "5m"], index=1, key="live_tf")
    view = bars[bars.timeframe == timeframe].sort_values("bar_time", ascending=False)
    st.caption("Auto-refreshes every 5 seconds. Outside market hours, exchange timestamps remain at the last market update.")
    st.dataframe(view, use_container_width=True, hide_index=True)
    if not view.empty:
        token = st.selectbox("Instrument token", view.token.drop_duplicates().tolist(), key="live_token")
        chart = view[view.token == token].sort_values("bar_time").set_index("bar_time")
        st.line_chart(chart[["close"]], use_container_width=True)


live_market_panel()
st.divider()

st.subheader("Historical replay & paper trading")
st.caption("Run from PowerShell: python run_backtest.py --days 90 --timeframe FIVE_MINUTE --style both")
if DB_PATH.exists():
    with sqlite3.connect(DB_PATH, timeout=5) as con:
        has_runs = table_exists(con, "backtest_runs")
        has_trades = table_exists(con, "backtest_trades")
        if has_runs:
            runs = pd.read_sql_query("SELECT * FROM backtest_runs ORDER BY created_at DESC LIMIT 20", con)
        else:
            runs = pd.DataFrame()
    if runs.empty:
        st.info("No backtests saved yet. Run python run_backtest.py after authenticating with Angel One.")
    else:
        run_id = st.selectbox("Backtest run", runs.run_id.tolist(), format_func=lambda rid: f"{rid} · {runs.loc[runs.run_id == rid, 'created_at'].iloc[0]}")
        run = runs[runs.run_id == run_id].iloc[0]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Trades", int(run.trade_count))
        m2.metric("Net P&L", f"₹{run.net_pnl:,.2f}")
        m3.metric("Win rate", f"{run.win_rate:.1f}%")
        m4.metric("Profit factor", f"{run.profit_factor:.2f}")
        m5.metric("Max drawdown", f"₹{run.max_drawdown:,.2f}")
        if "ending_equity" in run.index:
            st.metric("Ending portfolio equity", f"₹{run.ending_equity:,.2f}")
        st.caption(f"{run.days} trading sessions · {run.timeframe} · {run.styles} · {run.instrument_count} instruments")
        if has_trades:
            with sqlite3.connect(DB_PATH, timeout=5) as con:
                trades = pd.read_sql_query("SELECT * FROM backtest_trades WHERE run_id=? ORDER BY entry_time", con, params=(run_id,))
            if not trades.empty:
                styles = ["All"] + sorted(trades["style"].dropna().astype(str).unique().tolist())
                chosen_style = st.selectbox("Strategy style", styles, key="bt_style")
                if chosen_style != "All":
                    trades = trades[trades["style"].astype(str) == chosen_style]
                st.dataframe(trades.drop(columns=["id", "run_id"]), use_container_width=True, hide_index=True)
                st.subheader("Portfolio and strategy diagnostics")
                if {"risk_budget", "actual_risk", "allocated_capital"}.issubset(trades.columns):
                    st.caption("risk_budget is the requested risk ceiling; actual_risk is quantity × stop distance. allocated_capital reserves full notional, not broker margin.")
                by_style = trades.groupby("style", dropna=False).agg(trades=("net_pnl", "size"), net_pnl=("net_pnl", "sum"), win_rate=("net_pnl", lambda x: (x > 0).mean() * 100), avg_actual_risk=("actual_risk", "mean")).reset_index()
                by_symbol = trades.groupby(["symbol", "segment"], dropna=False).agg(trades=("net_pnl", "size"), net_pnl=("net_pnl", "sum"), win_rate=("net_pnl", lambda x: (x > 0).mean() * 100)).reset_index()
                st.markdown("**By strategy**")
                st.dataframe(by_style, use_container_width=True, hide_index=True)
                st.markdown("**By instrument**")
                st.dataframe(by_symbol, use_container_width=True, hide_index=True)
                equity = trades.sort_values(["exit_time", "entry_time"]).set_index("exit_time")["net_pnl"].cumsum()
                st.line_chart(equity, y_label="Cumulative portfolio P&L (₹)")
else:
    st.info("Run a backtest to initialize the local research database.")

st.divider()
st.subheader("Historical scanner snapshot")
if not DB_PATH.exists():
    st.info("Run python run_scanner.py to create scanner results.")
    st.stop()
with sqlite3.connect(DB_PATH, timeout=5) as con:
    if not table_exists(con, "scan_results"):
        st.info("No scanner results table yet. Run: python run_scanner.py")
        st.stop()
    df = pd.read_sql_query(
        """SELECT * FROM scan_results WHERE scan_time=(SELECT MAX(scan_time) FROM scan_results)
           ORDER BY score DESC""", con)
if df.empty:
    st.info("No scan results stored.")
else:
    st.caption(f"Last historical scanner run: {df.scan_time.iloc[0]}. This is not the live tick feed.")
    a, b, c = st.columns(3)
    a.metric("Candidates", len(df))
    b.metric("Bullish candidates", int((df.bias == "BULLISH_CANDIDATE").sum()))
    c.metric("Bearish candidates", int((df.bias == "BEARISH_CANDIDATE").sum()))
    st.dataframe(df.drop(columns=["id"]), use_container_width=True)
    st.subheader("Relative volume vs score")
    st.scatter_chart(df, x="rvol", y="score", color="segment")
