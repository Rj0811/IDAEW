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
