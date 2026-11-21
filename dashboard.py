import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src.iadew.config import settings
from src.iadew.depth_analytics import depth_metrics, liquidity_changes, rolling_depth_analysis

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
        if table_exists(con, "live_bars"):
            bars = pd.read_sql_query(
                """SELECT token, exchange_type, timeframe, bar_time, open, high, low, close,
                          volume, tick_count FROM live_bars ORDER BY bar_time DESC LIMIT 1000""", con)
        else:
            bars = pd.DataFrame()
        has_depth = table_exists(con, "depth_snapshots")
        if has_depth:
            depths = pd.read_sql_query(
                """SELECT d.* FROM depth_snapshots d
                   INNER JOIN (SELECT token, MAX(id) AS latest_id FROM depth_snapshots GROUP BY token) x
                   ON d.id=x.latest_id ORDER BY d.token""", con)
        else:
            depths = pd.DataFrame()

    if not bars.empty:
        bars["bar_time"] = pd.to_datetime(bars["bar_time"], errors="coerce")
        bars = bars.dropna(subset=["bar_time"])
        if not bars.empty:
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
            st.dataframe(view, use_container_width=True, hide_index=True)
            if not view.empty:
                token = st.selectbox("Instrument token", view.token.drop_duplicates().tolist(), key="live_token")
                chart = view[view.token == token].sort_values("bar_time").set_index("bar_time")
                st.line_chart(chart[["close"]], use_container_width=True)
    else:
        st.info("No live candle data stored yet. For candles run: python run_live_feed.py")

    st.subheader("NSE cash market depth analytics")
    if depths.empty:
        st.info("No depth snapshots stored yet. Run: python run_live_feed.py --depth")
    else:
        depths["received_timestamp"] = pd.to_datetime(depths["received_timestamp"], errors="coerce")
        token = st.selectbox("Depth instrument token", depths.token.tolist(), key="depth_token")
        selected = depths[depths.token == token].iloc[0]
        buys = json.loads(selected["buy_levels_json"])
        sells = json.loads(selected["sell_levels_json"])
        metrics = depth_metrics(buys, sells)
        with sqlite3.connect(DB_PATH, timeout=5) as con:
            previous = pd.read_sql_query(
                "SELECT * FROM depth_snapshots WHERE token=? AND id < ? ORDER BY id DESC LIMIT 1",
                con, params=(str(token), int(selected["id"])))
        history_rows = []
        with sqlite3.connect(DB_PATH, timeout=5) as con:
            recent = pd.read_sql_query(
                """SELECT received_timestamp, buy_levels_json, sell_levels_json
                   FROM depth_snapshots WHERE token=? ORDER BY id DESC LIMIT 1000""",
                con, params=(str(token),))
        for _, row in recent.iloc[::-1].iterrows():
            history_rows.append({
                "received_timestamp": row["received_timestamp"],
                "buys": json.loads(row["buy_levels_json"]),
                "sells": json.loads(row["sell_levels_json"]),
            })
        rolling_1m = rolling_depth_analysis(history_rows, 1)
        rolling_5m = rolling_depth_analysis(history_rows, 5)

        changes = []
        if not previous.empty:
            changes = liquidity_changes(
                json.loads(previous.iloc[0]["buy_levels_json"]),
                json.loads(previous.iloc[0]["sell_levels_json"]), buys, sells)

        st.markdown("**Current book metrics**")
        a, b, c, e = st.columns(4)
        a.metric("Best bid", f"₹{metrics['best_bid']:,.2f}" if metrics["best_bid"] is not None else "—")
        b.metric("Best ask", f"₹{metrics['best_ask']:,.2f}" if metrics["best_ask"] is not None else "—")
        c.metric("Spread", f"₹{metrics['spread']:,.2f}" if metrics["spread"] is not None else "—")
        e.metric("Weighted mid", f"₹{metrics['weighted_mid']:,.2f}" if metrics["weighted_mid"] is not None else "—")
        summary = [{
            "Depth": f"Top {n}", "Bid quantity": metrics[f"bid_qty_{n}"],
            "Ask quantity": metrics[f"ask_qty_{n}"],
            "Bid/ask imbalance": f"{metrics[f'imbalance_{n}']:+.1f}%"
        } for n in (5, 10, 20)]
        st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)
        st.caption("Imbalance = (bid quantity − ask quantity) / total displayed quantity. Positive means more displayed bid size; negative means more displayed ask size.")
        left, right = st.columns(2)
        with left:
            st.markdown("**Bid levels**")
            st.dataframe(pd.DataFrame(buys), use_container_width=True, hide_index=True)
        with right:
            st.markdown("**Ask levels**")
            st.dataframe(pd.DataFrame(sells), use_container_width=True, hide_index=True)
        st.markdown("**Displayed liquidity changes vs previous snapshot**")
        if changes:
            st.dataframe(pd.DataFrame(changes[:20]), use_container_width=True, hide_index=True)
        else:
            st.info("No prior snapshot available, or quantities at matching prices did not change.")
        stamp = selected["received_timestamp"]
        st.caption(f"Received: {stamp} · Exchange timestamp: {selected['exchange_timestamp'] or 'not supplied'} · Quality: {selected['quality_flags'] or 'OK'}")

        st.markdown("**Rolling depth pressure**")
        if rolling_1m and rolling_5m:
            st.caption(f"Samples in last 1m: {rolling_1m['samples']} · Samples in last 5m: {rolling_5m['samples']}")
            for label, data in (("1-minute", rolling_1m), ("5-minute", rolling_5m)):
                st.markdown(f"**{label} window**")
                pressure = pd.DataFrame([{
                    "Depth": f"Top {n}",
                    "Mean imbalance": f"{data[f'mean_imbalance_{n}']:+.1f}%",
                    "Bid-dominant persistence (≥ +15%)": f"{data[f'positive_persistence_{n}']:.0f}%",
                    "Ask-dominant persistence (≤ −15%)": f"{data[f'negative_persistence_{n}']:.0f}%"
                } for n in (5, 10, 20)])
                st.dataframe(pressure, use_container_width=True, hide_index=True)
            st.markdown("**Near-book vs deeper-book disagreement**")
            st.write(rolling_1m["divergence"])
            if rolling_1m["alert"] != "No divergence alert":
                st.warning("Observation alert: near/deep liquidity divergence persisted across at least 3 recent snapshots. This is not a trade-entry signal.")
            else:
                st.caption("No divergence alert: the minimum 3-snapshot condition is not met or near/deep pressure is not strongly opposed.")
        else:
            st.info("Rolling pressure requires timestamped snapshots. Keep the depth collector running to build a 1–5 minute sample history.")

        st.caption("Snapshot-to-snapshot observations do not prove cancellations, executions, queue movement, aggressive buying/selling, or trade intent.")

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
        if "ending_equity" in run.index and pd.notna(run.ending_equity) and float(run.ending_equity) > 0:
            st.metric("Ending portfolio equity", f"₹{run.ending_equity:,.2f}")
        st.caption(f"{run.days} requested trading sessions · {run.timeframe} · {run.styles} · {run.instrument_count} instruments")
        with sqlite3.connect(DB_PATH, timeout=5) as con:
            if table_exists(con, "replay_bars"):
                coverage = pd.read_sql_query("SELECT COUNT(*) AS bars, MIN(bar_time) AS first_bar, MAX(bar_time) AS last_bar FROM replay_bars WHERE run_id=?", con, params=(run_id,))
                if not coverage.empty and int(coverage.iloc[0]["bars"] or 0) > 0:
                    cv = coverage.iloc[0]
                    st.caption(f"Actual stored data coverage: {cv.first_bar} → {cv.last_bar} · {int(cv.bars):,} bars")
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


st.divider()
st.subheader("GoCharting visual intelligence")
st.caption("Rendered 5-minute chart captures and optional vision notes. Visual observations are not trade signals.")
visual_dir = Path(__file__).resolve().parent / "data" / "gocharting_captures"
if not visual_dir.exists():
    st.info("No GoCharting captures yet. Run: python run_gocharting_visual.py --symbols NIFTY BANKNIFTY RELIANCE")
else:
    capture_files = sorted(visual_dir.glob("*.json"), reverse=True)
    if not capture_files:
        st.info("Capture metadata not found yet. Start the GoCharting visual capture CLI.")
    else:
        capture_options = {}
        for meta_path in capture_files:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                label = f"{meta.get('captured_at_ist', '')} · {meta.get('instrument', 'UNKNOWN')} · {meta.get('timeframe_requested', '?')}"
                capture_options[label] = (meta_path, meta)
            except (OSError, json.JSONDecodeError):
                continue
        if capture_options:
            selected_label = st.selectbox("Captured chart", list(capture_options.keys()), key="visual_capture")
            meta_path, meta = capture_options[selected_label]
            image_path = Path(__file__).resolve().parent / meta.get("image_path", "")
            if image_path.exists():
                st.image(str(image_path), caption=f"{meta.get('instrument')} · requested {meta.get('timeframe_requested')} · {meta.get('captured_at_ist')}", use_container_width=True)
            else:
                st.warning("Screenshot file referenced by metadata is missing.")
            st.json({k: v for k, v in meta.items() if k not in {"image_path"}})
            analysis_path = meta.get("analysis_path")
            if analysis_path:
                note_path = Path(__file__).resolve().parent / analysis_path
                if note_path.exists():
                    st.markdown("**Vision assessment**")
                    st.markdown(note_path.read_text(encoding="utf-8"))
