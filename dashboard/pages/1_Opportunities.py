import time

import pandas as pd
import streamlit as st

from api_client import APIError, get, post
from time_utils import friendly_utc_timestamp, humanize_timestamp

st.set_page_config(page_title="Opportunities · Screener", page_icon="📊", layout="wide")
st.title("📊 Opportunities")

try:
    scans = get("/api/scans", limit=100)
except APIError as exc:
    st.error(str(exc))
    st.stop()

scan_options = {"All scans": None}
for scan in scans:
    label = (
        f"{humanize_timestamp(scan['started_at'])} · {scan['status']} · "
        f"{scan['qualified_count']} qualified"
    )
    scan_options[label] = scan["id"]

f1, f2, f3, f4 = st.columns([1.4, 1, 1, 2])
scan_label = f1.selectbox("Scan", options=list(scan_options.keys()))
qualified_only = f2.toggle("Qualified only")
min_score = f3.slider("Minimum score", 0, 100, 0)
search = f4.text_input("Search token, symbol, or pair")

try:
    rows = get(
        "/api/opportunities",
        qualified=True if qualified_only else None,
        min_score=min_score or None,
        scan_id=scan_options[scan_label],
        limit=500,
    )
except APIError as exc:
    st.error(str(exc))
    st.stop()

if search:
    needle = search.lower()
    rows = [
        row
        for row in rows
        if needle
        in " ".join(
            [
                row.get("symbol", ""),
                row.get("name", ""),
                row.get("pair_address", ""),
                row.get("token_address", ""),
            ]
        ).lower()
    ]

if not rows:
    st.info("No opportunities match these filters.")
    st.stop()

display_rows = []
for row in rows:
    created = row.get("pair_created_at")
    display_rows.append(
        {
            "Token": row["symbol"],
            "Score": row["score"],
            "Qualified": row["qualified"],
            "Created": humanize_timestamp(created),
            "Market cap": row["market_cap_usd"],
            "Liquidity": row["liquidity_usd"],
            "5m volume": row["volume_5m_usd"],
            "Buys": row["buys_5m"],
            "Sells": row["sells_5m"],
            "Pair": row["pair_address"],
        }
    )
st.dataframe(
    pd.DataFrame(display_rows),
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

def move_carousel(step: int) -> None:
    st.session_state.carousel_index = (
        st.session_state.get("carousel_index", 0) + step
    ) % len(rows)
    st.session_state.carousel_last_advance = time.time()


def send_pair_to_discord(pair_address: str) -> None:
    try:
        post(f"/api/opportunities/{pair_address}/send-to-discord")
        st.session_state.discord_monitor_result = (
            pair_address,
            True,
            "Sent to Discord and added to performance monitoring.",
        )
    except APIError as exc:
        st.session_state.discord_monitor_result = (
            pair_address,
            False,
            str(exc),
        )
    st.session_state.carousel_last_advance = time.time()


@st.fragment(run_every="6s")
def token_carousel() -> None:
    if "carousel_index" not in st.session_state:
        st.session_state.carousel_index = 0
    if "carousel_last_advance" not in st.session_state:
        st.session_state.carousel_last_advance = time.time()

    st.session_state.carousel_index %= len(rows)
    controls = st.columns([1, 1, 4, 1.5])
    controls[0].button(
        "← Previous",
        use_container_width=True,
        on_click=move_carousel,
        args=(-1,),
    )
    controls[1].button(
        "Next →",
        use_container_width=True,
        on_click=move_carousel,
        args=(1,),
    )
    auto_rotate = controls[3].toggle(
        "Auto-rotate",
        value=True,
        key="carousel_auto_rotate",
        help="Move to the next token every six seconds.",
    )

    now = time.time()
    if auto_rotate and now - st.session_state.carousel_last_advance >= 5.5:
        st.session_state.carousel_index = (
            st.session_state.carousel_index + 1
        ) % len(rows)
        st.session_state.carousel_last_advance = now

    index = st.session_state.carousel_index
    item = rows[index]
    controls[2].markdown(
        f"**Token {index + 1} of {len(rows)}** · rotating every 6 seconds"
        if auto_rotate
        else f"**Token {index + 1} of {len(rows)}** · paused"
    )

    st.subheader(f"{item['name']} ({item['symbol']})")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Score", f"{item['score']}/100")
    m2.metric("Price", f"${item['price_usd'] or 0:,.8f}")
    m3.metric("Market cap", f"${item['market_cap_usd'] or 0:,.0f}")
    m4.metric("Liquidity", f"${item['liquidity_usd'] or 0:,.0f}")
    if item.get("pair_created_at"):
        st.caption(
            f"Pair created {humanize_timestamp(item['pair_created_at'])} · "
            f"{friendly_utc_timestamp(item['pair_created_at'])} · "
            "This is the DEX pair creation time, not necessarily the token mint time."
        )
    else:
        st.caption("Pair creation time was not supplied by DEX Screener.")

    left, right = st.columns(2)
    with left:
        st.markdown("**Score breakdown**")
        breakdown = pd.DataFrame(
            {
                "Category": item["score_breakdown"].keys(),
                "Points": item["score_breakdown"].values(),
            }
        )
        st.bar_chart(breakdown.set_index("Category"))
    with right:
        st.markdown("**Research checks**")
        for key, value in item["checks"].items():
            icon = "✅" if value is True else "❌" if value is False else "❓"
            st.write(f"{icon} {key.replace('_', ' ').title()}: {value}")
        for reason in item["rejection_reasons"]:
            st.write(f"• {reason}")

    token = item["token_address"]
    pair = item["pair_address"]
    st.markdown(
        f"[DEX Screener](https://dexscreener.com/solana/{pair}) · "
        f"[Solscan](https://solscan.io/token/{token}) · "
        f"[Jupiter](https://jup.ag/swap/SOL-{token})"
    )
    st.button(
        "📨 Send to Discord & monitor",
        type="primary",
        use_container_width=True,
        key=f"send_to_discord_{pair}",
        on_click=send_pair_to_discord,
        args=(pair,),
        help="Manual override: sends this pair even if it did not pass every automatic filter.",
    )
    result = st.session_state.get("discord_monitor_result")
    if result and result[0] == pair:
        if result[1]:
            st.success(result[2])
        else:
            st.error(result[2])
    st.code(token, language=None)


st.subheader("Token carousel")
token_carousel()
