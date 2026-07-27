from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from api_client import APIError, get

st.set_page_config(page_title="Opportunities · Screener", page_icon="📊", layout="wide")
st.title("📊 Opportunities")

f1, f2, f3 = st.columns([1, 1, 2])
qualified_only = f1.toggle("Qualified only")
min_score = f2.slider("Minimum score", 0, 100, 0)
search = f3.text_input("Search token, symbol, or pair")

try:
    rows = get(
        "/api/opportunities",
        qualified=True if qualified_only else None,
        min_score=min_score or None,
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
    age = None
    if created:
        age = round(
            (datetime.now(UTC) - datetime.fromisoformat(created)).total_seconds() / 60
        )
    display_rows.append(
        {
            "Token": row["symbol"],
            "Score": row["score"],
            "Qualified": row["qualified"],
            "Age (min)": age,
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
        "Market cap": st.column_config.NumberColumn(format="$%.0f"),
        "Liquidity": st.column_config.NumberColumn(format="$%.0f"),
        "5m volume": st.column_config.NumberColumn(format="$%.0f"),
    },
)

selected_pair = st.selectbox(
    "Inspect token",
    options=[row["pair_address"] for row in rows],
    format_func=lambda address: next(
        f"{row['symbol']} · {row['score']}/100"
        for row in rows
        if row["pair_address"] == address
    ),
)
item = next(row for row in rows if row["pair_address"] == selected_pair)
st.subheader(f"{item['name']} ({item['symbol']})")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Score", f"{item['score']}/100")
m2.metric("Price", f"${item['price_usd'] or 0:,.8f}")
m3.metric("Market cap", f"${item['market_cap_usd'] or 0:,.0f}")
m4.metric("Liquidity", f"${item['liquidity_usd'] or 0:,.0f}")

left, right = st.columns(2)
with left:
    st.markdown("**Score breakdown**")
    breakdown = pd.DataFrame(
        {"Category": item["score_breakdown"].keys(), "Points": item["score_breakdown"].values()}
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
st.code(token, language=None)

