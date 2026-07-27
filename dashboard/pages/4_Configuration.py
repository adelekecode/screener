import streamlit as st

from api_client import APIError, get, patch, post

st.set_page_config(page_title="Configuration · Screener", page_icon="⚙️", layout="wide")
st.title("⚙️ Configuration")
st.caption("Changes are stored by the FastAPI backend and apply to future scans.")

try:
    settings = get("/api/settings")
except APIError as exc:
    st.error(str(exc))
    st.stop()

criteria = settings["criteria"]
with st.form("criteria"):
    a, b, c = st.columns(3)
    interval = a.number_input(
        "Scan interval (minutes)", 1, 1440, settings["scan_interval_minutes"]
    )
    min_age = a.number_input(
        "Minimum pair age (minutes)", 0, 10080, criteria["minimum_pair_age_minutes"]
    )
    max_age = a.number_input(
        "Maximum pair age (minutes)", 1, 10080, criteria["maximum_pair_age_minutes"]
    )
    min_liquidity = b.number_input(
        "Minimum liquidity (USD)", 0.0, value=float(criteria["minimum_liquidity_usd"])
    )
    min_market_cap = b.number_input(
        "Minimum market cap (USD)", 0.0, value=float(criteria["minimum_market_cap_usd"])
    )
    max_market_cap = b.number_input(
        "Maximum market cap (USD)", 0.0, value=float(criteria["maximum_market_cap_usd"])
    )
    min_volume = c.number_input(
        "Minimum recent volume (USD)", 0.0, value=float(criteria["minimum_volume_10m_usd"])
    )
    min_buys = c.number_input(
        "Minimum recent buys", 0, value=criteria["minimum_buys_10m"]
    )
    ratio = c.number_input(
        "Minimum buy/sell ratio", 0.0, value=float(criteria["minimum_buy_sell_ratio"])
    )
    alert_score = c.slider(
        "Minimum alert score", 0, 100, criteria["minimum_score_for_alert"]
    )
    st.markdown("**On-chain safety requirements**")
    s1, s2, s3 = st.columns(3)
    min_unique_buyers = s1.number_input(
        "Minimum unique buyers",
        0,
        value=criteria["minimum_unique_buyers_10m"],
        help="DEX Screener does not provide this field. Keep at zero only if you accept that limitation.",
    )
    max_top_10 = s1.number_input(
        "Maximum top-10 holders (%)",
        0.0,
        100.0,
        value=float(criteria["maximum_top_10_holder_percentage"]),
    )
    max_creator = s2.number_input(
        "Maximum creator allocation (%)",
        0.0,
        100.0,
        value=float(criteria["maximum_creator_percentage"]),
    )
    require_mint_revoked = s2.checkbox(
        "Require revoked mint authority",
        value=criteria["require_mint_authority_revoked"],
    )
    require_freeze_revoked = s3.checkbox(
        "Require revoked freeze authority",
        value=criteria["require_freeze_authority_revoked"],
    )
    st.caption(
        "Unknown required checks fail closed. Disabling a requirement should be a deliberate "
        "research-risk decision."
    )
    submitted = st.form_submit_button("Save filtering criteria", type="primary")
    if submitted:
        try:
            patch(
                "/api/settings",
                {
                    "scan_interval_minutes": interval,
                    "criteria": {
                        "minimum_pair_age_minutes": min_age,
                        "maximum_pair_age_minutes": max_age,
                        "minimum_liquidity_usd": min_liquidity,
                        "minimum_market_cap_usd": min_market_cap,
                        "maximum_market_cap_usd": max_market_cap,
                        "minimum_volume_10m_usd": min_volume,
                        "minimum_buys_10m": min_buys,
                        "minimum_buy_sell_ratio": ratio,
                        "minimum_unique_buyers_10m": min_unique_buyers,
                        "maximum_top_10_holder_percentage": max_top_10,
                        "maximum_creator_percentage": max_creator,
                        "require_mint_authority_revoked": require_mint_revoked,
                        "require_freeze_authority_revoked": require_freeze_revoked,
                        "minimum_score_for_alert": alert_score,
                    },
                },
            )
            st.success("Settings saved.")
        except APIError as exc:
            st.error(str(exc))

st.divider()
st.subheader("Discord")
with st.form("discord"):
    webhook = st.text_input(
        "Discord webhook URL",
        type="password",
        placeholder="Leave blank to disable notifications",
        help="The existing URL is never returned by the API.",
    )
    if settings["discord_configured"]:
        st.caption("A Discord webhook is currently configured.")
    if st.form_submit_button("Update webhook"):
        try:
            patch("/api/settings", {"discord_webhook_url": webhook})
            st.success("Discord setting updated.")
        except APIError as exc:
            st.error(str(exc))

st.divider()
st.subheader("Scanner state")
if settings["scanner_paused"]:
    if st.button("Resume scanner"):
        post("/api/scanner/resume")
        st.rerun()
else:
    if st.button("Pause scanner"):
        post("/api/scanner/pause")
        st.rerun()
