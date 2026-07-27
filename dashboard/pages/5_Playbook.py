import pandas as pd
import streamlit as st

st.set_page_config(page_title="Playbook · Screener", page_icon="📘", layout="wide")

st.title("📘 Scanner playbook")
st.caption(
    "How to operate the scanner, read every metric, and turn an alert into a structured "
    "manual research decision."
)

st.warning(
    "The scanner is a research and alerting assistant—not a buy signal. It does not connect "
    "to a wallet or execute trades. A high score can still lead to a total loss."
)

workflow, table_guide, scoring, checks, alerts = st.tabs(
    ["How to use it", "Table metrics", "Score", "Safety checks", "Alerts & review"]
)

with workflow:
    st.subheader("A repeatable workflow")
    st.markdown(
        """
1. **Configure your rules.** Open **Configuration** and review the pair-age, liquidity,
   market-cap, activity, holder, authority, and score thresholds. Start with the conservative
   defaults.
2. **Start or wait for a scan.** Use **Run now** for an immediate scan, or leave the scanner
   running for its scheduled interval. The Redis lock prevents two scans from processing at
   the same time.
3. **Check Scan History.** Confirm the latest scan completed. “Discovered” is the number of
   token profiles found; “Processed” is the number of new, non-duplicate pairs researched.
4. **Triage Opportunities.** Sort mentally by **Qualified**, then **Score**, while checking
   liquidity, age, volume, and the balance between buys and sells.
5. **Inspect the token.** Select a row below the table. Read its score breakdown, every
   rejection reason, and every unknown check. Open DEX Screener and Solscan from the supplied
   links and verify the contract address.
6. **Treat Discord as a prompt to research.** An alert means the pair passed the configured
   rules at scan time. It does not mean conditions remain unchanged.
7. **Review outcomes.** Use **Alert History** to compare the initial price with current price,
   maximum gain, and maximum decline. Adjust criteria only after reviewing a useful sample,
   not after one winner or loser.
        """
    )

    st.subheader("What the status numbers mean")
    status_rows = [
        {
            "Status": "Discovered",
            "Meaning": "Solana token profiles returned by the discovery source in that scan.",
        },
        {
            "Status": "Processed",
            "Meaning": "New pair records actually enriched, filtered, scored, and saved.",
        },
        {
            "Status": "Qualified",
            "Meaning": "Pairs with no rejection reasons and a score at or above the alert threshold.",
        },
        {
            "Status": "Alerted",
            "Meaning": "Qualified pairs successfully delivered to the configured Discord webhook.",
        },
    ]
    st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)

    st.info(
        "A low Processed count is not necessarily an error. Redis ignores recently processed "
        "pairs so they are not repeatedly analyzed or alerted."
    )

with table_guide:
    st.subheader("Every column in the Opportunities table")
    metric_rows = [
        {
            "Column": "Token",
            "What it is": "The token symbol reported by DEX Screener.",
            "How to read it": "A convenient label only.",
            "Watch out for": "Symbols are not unique and can be copied. Verify the contract address.",
        },
        {
            "Column": "Score",
            "What it is": "A 0–100 research score calculated from seven weighted categories.",
            "How to read it": "Higher means the observed data better matches your configured criteria.",
            "Watch out for": "It is not a probability of profit. Missing checks earn zero points.",
        },
        {
            "Column": "Qualified",
            "What it is": "Whether the pair passed every hard filter and met the alert score.",
            "How to read it": "True is eligible for an alert; False has one or more rejection reasons.",
            "Watch out for": "Qualification is a snapshot. Liquidity and permissions can change.",
        },
        {
            "Column": "Created",
            "What it is": "The liquidity pair creation timestamp reported by DEX Screener.",
            "How to read it": "Shown as relative time, such as “12 min ago” or “3 hrs ago.”",
            "Watch out for": "This is not necessarily the token mint time; one token can have several pairs.",
        },
        {
            "Column": "Market cap",
            "What it is": "DEX Screener market cap, falling back to fully diluted valuation when absent.",
            "How to read it": "Approximate network value used to keep candidates inside your chosen range.",
            "Watch out for": "Supply metadata or thin trading can make this estimate unreliable.",
        },
        {
            "Column": "Liquidity",
            "What it is": "Estimated USD value currently available in the pair's liquidity pool.",
            "How to read it": "More liquidity generally supports larger trades with less price impact.",
            "Watch out for": "Liquidity can be removed, may not be locked, and does not guarantee an exit.",
        },
        {
            "Column": "5m volume",
            "What it is": "Reported USD trading volume during DEX Screener's latest five-minute bucket.",
            "How to read it": "Shows very recent trading activity and momentum.",
            "Watch out for": "Volume may be wash trading. The scanner uses this as a conservative lower bound for its recent-volume rule.",
        },
        {
            "Column": "Buys",
            "What it is": "Buy transactions reported in the latest five-minute bucket.",
            "How to read it": "Compare it with Sells; sustained buying with real selling activity is healthier than buys alone.",
            "Watch out for": "Transaction count is not unique buyers. One wallet can create many buys.",
        },
        {
            "Column": "Sells",
            "What it is": "Sell transactions reported in the latest five-minute bucket.",
            "How to read it": "Some selling shows that exits are occurring. It also determines the buy/sell ratio.",
            "Watch out for": "Zero sells is rejected because it can indicate a very new, illiquid, or restricted market.",
        },
        {
            "Column": "Pair",
            "What it is": "The unique Solana liquidity-pool address.",
            "How to read it": "Use it to identify the exact market rather than relying on token name or symbol.",
            "Watch out for": "This differs from the token contract address shown in the detail view.",
        },
    ]
    guide = pd.DataFrame(metric_rows)
    st.dataframe(
        guide,
        hide_index=True,
        use_container_width=True,
        height=620,
        column_config={
            "Column": st.column_config.TextColumn(width="small"),
            "What it is": st.column_config.TextColumn(width="medium"),
            "How to read it": st.column_config.TextColumn(width="large"),
            "Watch out for": st.column_config.TextColumn(width="large"),
        },
    )

    st.subheader("Filters above the table")
    st.markdown(
        """
- **Qualified only** hides rejected candidates.
- **Minimum score** hides candidates below the chosen score without changing scanner settings.
- **Search** matches a token symbol, token name, pair address, or token contract address.

These controls change only what you see. They do not change scanning or alert rules.
        """
    )

with scoring:
    st.subheader("How the 100-point score works")
    score_rows = [
        {
            "Category": "Liquidity",
            "Maximum": 20,
            "How points are earned": "Rises toward full points at twice the configured minimum liquidity.",
        },
        {
            "Category": "Volume and momentum",
            "Maximum": 20,
            "How points are earned": "Rises toward full points at twice the configured recent-volume minimum.",
        },
        {
            "Category": "Buy/sell activity",
            "Maximum": 15,
            "How points are earned": "60% from buy count and 40% from the buy/sell ratio.",
        },
        {
            "Category": "Holder distribution",
            "Maximum": 20,
            "How points are earned": "More points when the top ten token accounts control less supply.",
        },
        {
            "Category": "Token permissions",
            "Maximum": 15,
            "How points are earned": "7.5 points each for verified revoked mint and freeze authorities.",
        },
        {
            "Category": "Pair maturity",
            "Maximum": 5,
            "How points are earned": "Highest near the middle of the configured pair-age window.",
        },
        {
            "Category": "Social information",
            "Maximum": 5,
            "How points are earned": "Presence of a website or social link; identity is not verified.",
        },
    ]
    st.dataframe(pd.DataFrame(score_rows), hide_index=True, use_container_width=True)

    st.markdown(
        """
The score ranks candidates that look stronger on the available data. **Hard filters remain
separate:** a token can have a respectable score and still be unqualified because it fails
one required rule. Missing on-chain information receives no safety points.
        """
    )

with checks:
    st.subheader("Research checks and rejection reasons")
    check_rows = [
        {
            "Check": "Mint authority revoked",
            "Meaning": "No authority can mint additional supply through the token mint.",
            "Failure risk": "An active mint authority may create and sell more tokens.",
        },
        {
            "Check": "Freeze authority revoked",
            "Meaning": "No authority can freeze token accounts through the mint.",
            "Failure risk": "An active freeze authority may restrict holders.",
        },
        {
            "Check": "Top-10 holder percentage",
            "Meaning": "Share of raw token supply held by the ten largest token accounts.",
            "Failure risk": "High concentration increases coordinated selling and manipulation risk.",
        },
        {
            "Check": "Creator percentage",
            "Meaning": "Estimated share controlled by the creator when that data is available.",
            "Failure risk": "A large allocation can create heavy insider selling pressure.",
        },
        {
            "Check": "Unique buyers",
            "Meaning": "Distinct wallets buying during the recent period.",
            "Failure risk": "Transaction totals can look active while coming from very few wallets.",
        },
    ]
    st.dataframe(pd.DataFrame(check_rows), hide_index=True, use_container_width=True)

    st.markdown(
        """
**Check symbols**

- ✅ The check was available and passed.
- ❌ The check was available and failed.
- ❓ The data was unavailable; it is never silently treated as safe.

The default unique-buyer minimum is strict, while DEX Screener does not supply unique-buyer
data. Candidates therefore fail closed unless another source supplies it or you deliberately
set the minimum to `0` in Configuration.
        """
    )

    st.warning(
        "Largest token accounts are not the same as beneficial owners. A single owner can split "
        "tokens across wallets, while exchange, liquidity, or burn accounts can distort the list."
    )

with alerts:
    st.subheader("Reading Alert History")
    alert_rows = [
        {
            "Metric": "Initial price",
            "Meaning": "DEX Screener price saved when the Discord delivery was attempted.",
        },
        {
            "Metric": "Current price",
            "Meaning": "Most recent tracked DEX Screener price for that pair.",
        },
        {
            "Metric": "Max gain",
            "Meaning": "Highest tracked price relative to the initial price, expressed as a percentage.",
        },
        {
            "Metric": "Max decline",
            "Meaning": "Lowest tracked price relative to the initial price, expressed as a percentage.",
        },
        {
            "Metric": "Last tracked",
            "Meaning": "When the performance figures were most recently refreshed.",
        },
        {
            "Metric": "Error",
            "Meaning": "Discord delivery or tracking issue recorded for that attempt.",
        },
    ]
    st.dataframe(pd.DataFrame(alert_rows), hide_index=True, use_container_width=True)

    st.markdown(
        """
### Manual review checklist

Before making any decision outside this app:

- Match the contract address across the dashboard, DEX Screener, and Solscan.
- Recheck mint and freeze authorities; scan-time values can become stale.
- Inspect holders and transfers for linked wallets and concentrated supply.
- Confirm liquidity depth and whether liquidity can be removed.
- Compare volume with transaction size and wallet diversity for wash trading.
- Test whether both buys and sells are occurring in the actual pool.
- Treat websites and social profiles as unverified claims.
- Decide your maximum loss before considering an entry.
        """
    )

    st.info(
        "Tracked gain and decline use observed snapshots, not every trade tick. They do not include "
        "slippage, fees, taxes, failed transactions, or whether the quoted liquidity could support "
        "your position size."
    )
