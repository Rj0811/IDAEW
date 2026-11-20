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
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


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
            """SELECT token, exchange_type, timeframe, bar_time, open, high, low,
                      close, volume, tick_count
               FROM live_bars
               ORDER BY bar_time DESC LIMIT 1000""", con
        )

    if bars.empty:
        st.warning("No live ticks have been persisted yet. Keep run_live_feed.py running and check during market hours.")
        return

    bars["bar_time"] = pd.to_datetime(bars["bar_time"], errors="coerce")
    bars = bars.dropna(subset=["bar_time"])
    if bars.empty:
        st.warning("No valid exchange timestamps found in live candle data.")
        return

    latest = bars.sort_values("bar_time").iloc[-1]
    latest_time = latest["bar_time"]
    if latest_time.tzinfo is None:
        latest_time = latest_time.tz_localize(IST)
    else:
        latest_time = latest_time.tz_convert(IST)
    age_seconds = max(0, int((datetime.now(IST) - latest_time.to_pydatetime()).total_seconds()))
    a, b, c = st.columns(3)
    a.metric("Latest exchange candle", latest_time.strftime("%d %b %Y, %H:%M:%S IST"))
    b.metric("Latest close", f"₹{float(latest['close']):,.2f}")
    c.metric("Exchange data age", f"{age_seconds // 60}m {age_seconds % 60}s")

    timeframe = st.selectbox("Live candle timeframe", ["1m", "5m"], index=1, key="live_tf")
    view = bars[bars["timeframe"] == timeframe].sort_values("bar_time", ascending=False)
    st.caption("This panel refreshes every 5 seconds. Candle timestamps use exchange time, not the computer's scan time. Outside market hours, the latest exchange candle will naturally remain at the last market update.")
    st.dataframe(view, use_container_width=True, hide_index=True)
    if not view.empty:
        tokens = view["token"].drop_duplicates().tolist()
        token = st.selectbox("Instrument token", tokens, key="live_token")
        chart = view[view["token"] == token].sort_values("bar_time").set_index("bar_time")
        st.line_chart(chart[["close"]], use_container_width=True)


live_market_panel()

st.divider()
st.subheader("Scanner snapshot (historical scan results)")
if not DB_PATH.exists():
    st.info("Run python run_scanner.py to create scanner results.")
    st.stop()

with sqlite3.connect(DB_PATH, timeout=5) as con:
    if not table_exists(con, "scan_results"):
        st.info("No scanner results table yet. Run: python run_scanner.py")
        st.stop()
    df = pd.read_sql_query(
        """SELECT * FROM scan_results
           WHERE scan_time=(SELECT MAX(scan_time) FROM scan_results)
           ORDER BY score DESC""", con
    )

if df.empty:
    st.info("No scan results stored.")
else:
    scan_stamp = str(df["scan_time"].iloc[0])
    st.caption(f"Last historical scanner run: {scan_stamp}. This table is not the live tick feed.")
    a, b, c = st.columns(3)
    a.metric("Candidates", len(df))
    a.metric("Bullish candidates", int((df.bias == "BULLISH_CANDIDATE").sum()))
    c.metric("Bearish candidates", int((df.bias == "BEARISH_CANDIDATE").sum()))
    st.dataframe(df.drop(columns=["id"]), use_container_width=True)
    st.subheader("Relative volume vs score")
    st.scatter_chart(df, x="rvol", y="score", color="segment")
