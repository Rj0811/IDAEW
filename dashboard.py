import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="IADEW", layout="wide")
st.title("IADEW — Institutional Activity Watchlist")
st.caption("Research dashboard. Scores are heuristics, not probabilities or proof of institutional participation.")
db = Path("data/iadew.sqlite3")
if not db.exists():
    st.info("Run python run_scanner.py first.")
    st.stop()

with sqlite3.connect(db) as con:
    df = pd.read_sql_query(
        "SELECT * FROM scan_results WHERE scan_time=(SELECT MAX(scan_time) FROM scan_results) ORDER BY score DESC",
        con
    )
    live_tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='live_bars'", con
    )

st.subheader("Scanner")
if df.empty:
    st.info("No scan results stored.")
else:
    a, b, c = st.columns(3)
    a.metric("Candidates", len(df))
    b.metric("Bullish candidates", int((df.bias == "BULLISH_CANDIDATE").sum()))
    c.metric("Bearish candidates", int((df.bias == "BEARISH_CANDIDATE").sum()))
    st.dataframe(df.drop(columns=["id"]), use_container_width=True)
    st.subheader("Relative volume vs score")
    st.scatter_chart(df, x="rvol", y="score", color="segment")

st.divider()
st.subheader("Live market candles")
if live_tables.empty:
    st.info("No live candle database yet. In a second PowerShell window, run: python run_live_feed.py")
else:
    with sqlite3.connect(db) as con:
        bars = pd.read_sql_query(
            """SELECT token, exchange_type, timeframe, bar_time, open, high, low,
                      close, volume, tick_count
               FROM live_bars
               ORDER BY bar_time DESC LIMIT 500""", con
        )
    if bars.empty:
        st.info("Waiting for WebSocket ticks. Keep python run_live_feed.py running.")
    else:
        bars["bar_time"] = pd.to_datetime(bars["bar_time"])
        timeframe = st.selectbox("Candle timeframe", ["1m", "5m"], index=1)
        selected = bars[bars["timeframe"] == timeframe].sort_values("bar_time")
        st.caption("Prices are normalized to rupees. Volume is based on changes in cumulative day volume; the first observed packet per token establishes the baseline.")
        st.dataframe(selected, use_container_width=True, hide_index=True)
        token = st.selectbox("Instrument token", selected["token"].drop_duplicates().tolist())
        chart = selected[selected["token"] == token].set_index("bar_time")[["open", "high", "low", "close"]]
        if not chart.empty:
            st.line_chart(chart[["close"]], use_container_width=True)
