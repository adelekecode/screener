import pandas as pd
import streamlit as st

from api_client import APIError, get, post

st.set_page_config(page_title="Alert history · Screener", page_icon="🔔", layout="wide")
st.title("🔔 Alert history")
st.caption("Discord delivery records and initial snapshots.")

try:
    alerts = get("/api/alerts", limit=500)
except APIError as exc:
    st.error(str(exc))
    st.stop()

if not alerts:
    st.info("No alerts have been attempted yet.")
    st.stop()

frame = pd.DataFrame(alerts)
st.dataframe(
    frame[
        [
            "sent_at",
            "pair_address",
            "success",
            "initial_price_usd",
            "current_price_usd",
            "maximum_gain_percentage",
            "maximum_decline_percentage",
            "last_tracked_at",
            "error",
        ]
    ],
    hide_index=True,
    use_container_width=True,
    column_config={
        "initial_price_usd": st.column_config.NumberColumn("Initial price", format="$%.8f"),
        "current_price_usd": st.column_config.NumberColumn("Current price", format="$%.8f"),
        "maximum_gain_percentage": st.column_config.NumberColumn("Max gain", format="%.2f%%"),
        "maximum_decline_percentage": st.column_config.NumberColumn(
            "Max decline", format="%.2f%%"
        ),
    },
)
alert_id = st.selectbox(
    "Alert to resend",
    options=[alert["id"] for alert in alerts],
    format_func=lambda identifier: next(
        f"{alert['pair_address'][:12]}… · {alert['sent_at']}"
        for alert in alerts
        if alert["id"] == identifier
    ),
)
if st.button("Resend selected alert"):
    try:
        post(f"/api/alerts/{alert_id}/resend")
        st.success("Alert delivered to Discord.")
    except APIError as exc:
        st.error(str(exc))

st.caption(
    "Performance is refreshed on the scan interval using DEX Screener prices. "
    "It is research data, not an executable return."
)
