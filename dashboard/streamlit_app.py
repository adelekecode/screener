import pandas as pd
import streamlit as st

from api_client import APIError, get, post
from time_utils import friendly_utc_timestamp, humanize_timestamp

st.set_page_config(
    page_title="Screener",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔬 Screener")
st.caption("Local Solana research and alerts — no wallet connection, no automated trading.")

try:
    health = get("/health")
    stats = get("/api/stats")
except APIError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    st.subheader("Scanner controls")
    status_label = "Paused" if stats["scanner_paused"] else "Running"
    st.write(f"Status: **{status_label}**")
    left, right = st.columns(2)
    if left.button("Run now", use_container_width=True, disabled=stats["scanner_paused"]):
        try:
            post("/api/scans/run")
            st.success("Scan accepted")
        except APIError as exc:
            st.warning(str(exc))
    action = "/api/scanner/resume" if stats["scanner_paused"] else "/api/scanner/pause"
    label = "Resume" if stats["scanner_paused"] else "Pause"
    if right.button(label, use_container_width=True):
        try:
            post(action)
            st.rerun()
        except APIError as exc:
            st.error(str(exc))

cols = st.columns(6)
cols[0].metric("API", health["status"].title())
cols[1].metric("Database", health["database"].title())
cols[2].metric("Pairs saved", stats["opportunities"])
cols[3].metric("Qualified", stats["qualified"])
cols[4].metric("Alerts today", stats["alerts_today"])
cols[5].metric("Scans", stats["scans"])

last_scan = stats.get("last_scan")
st.subheader("Scanner activity")
if not last_scan:
    st.info("No scan has run yet. Choose “Run now” or wait for the next scheduled scan.")
else:
    a, b, c, d = st.columns(4)
    a.metric("Last scan", last_scan["status"].title())
    b.metric("Discovered tokens", last_scan["discovered_count"])
    c.metric("Pairs processed", last_scan["processed_count"])
    d.metric("Alerts sent", last_scan["alerted_count"])
    st.caption(
        f"Started {humanize_timestamp(last_scan['started_at'])} · "
        f"{friendly_utc_timestamp(last_scan['started_at'])}"
    )
    if last_scan.get("error"):
        st.error(last_scan["error"])

st.subheader("Recent opportunities")
try:
    rows = get("/api/opportunities", limit=10)
    if rows:
        frame = pd.DataFrame(rows)
        frame["pair_created_at"] = frame["pair_created_at"].map(humanize_timestamp)
        recent = frame[
            [
                "symbol",
                "score",
                "qualified",
                "pair_created_at",
                "market_cap_usd",
                "liquidity_usd",
                "volume_5m_usd",
                "buys_5m",
                "sells_5m",
            ]
        ].rename(
            columns={
                "symbol": "Token",
                "score": "Score",
                "qualified": "Qualified",
                "pair_created_at": "Created",
                "market_cap_usd": "Market cap",
                "liquidity_usd": "Liquidity",
                "volume_5m_usd": "5m volume",
                "buys_5m": "Buys",
                "sells_5m": "Sells",
            }
        )
        st.dataframe(
            recent,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Created": st.column_config.TextColumn(
                    help="How long ago DEX Screener reports that the pair was created."
                ),
                "Market cap": st.column_config.NumberColumn(format="$%.0f"),
                "Liquidity": st.column_config.NumberColumn(format="$%.0f"),
                "5m volume": st.column_config.NumberColumn(format="$%.0f"),
            },
        )
    else:
        st.info("Newly discovered pairs will appear here after the first scan.")
except APIError as exc:
    st.error(str(exc))

st.warning(
    "This dashboard is a research assistant, not a buy signal. Memecoins can lose all "
    "their value; verify every contract and trade manually."
)
