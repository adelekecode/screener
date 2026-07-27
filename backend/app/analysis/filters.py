from datetime import UTC, datetime
from typing import Any

from app.config import Criteria


def _below(value: float | int | None, threshold: float | int) -> bool:
    return value is None or value < threshold


def apply_filters(candidate: dict[str, Any], checks: dict[str, Any], criteria: Criteria) -> list[str]:
    reasons: list[str] = []
    now = datetime.now(UTC)
    created_at = candidate.get("pair_created_at")
    age_minutes = (now - created_at).total_seconds() / 60 if created_at else None

    if age_minutes is None:
        reasons.append("Pair creation time is unavailable")
    elif age_minutes < criteria.minimum_pair_age_minutes:
        reasons.append("Pair is too new")
    elif age_minutes > criteria.maximum_pair_age_minutes:
        reasons.append("Pair is older than the discovery window")

    if _below(candidate.get("liquidity_usd"), criteria.minimum_liquidity_usd):
        reasons.append("Liquidity is below the minimum")

    market_cap = candidate.get("market_cap_usd")
    if market_cap is None:
        reasons.append("Market cap is unavailable")
    elif not criteria.minimum_market_cap_usd <= market_cap <= criteria.maximum_market_cap_usd:
        reasons.append("Market cap is outside the configured range")

    if _below(candidate.get("volume_10m_usd"), criteria.minimum_volume_10m_usd):
        reasons.append("Recent volume is below the minimum")
    if _below(candidate.get("buys_10m"), criteria.minimum_buys_10m):
        reasons.append("Recent buys are below the minimum")

    unique_buyers = candidate.get("unique_buyers_10m")
    if criteria.minimum_unique_buyers_10m and unique_buyers is None:
        reasons.append("Unique buyer count is unavailable")
    elif _below(unique_buyers, criteria.minimum_unique_buyers_10m):
        reasons.append("Unique buyer count is below the minimum")

    buys = candidate.get("buys_10m") or 0
    sells = candidate.get("sells_10m") or 0
    ratio = buys / sells if sells else (float("inf") if buys else 0)
    if ratio < criteria.minimum_buy_sell_ratio:
        reasons.append("Buy/sell ratio is below the minimum")
    if sells == 0:
        reasons.append("No recent selling activity")

    top_10 = checks.get("top_10_holder_percentage")
    if top_10 is None:
        reasons.append("Holder concentration is unavailable")
    elif top_10 > criteria.maximum_top_10_holder_percentage:
        reasons.append("Top holder concentration is too high")

    creator = checks.get("creator_percentage")
    if creator is not None and creator > criteria.maximum_creator_percentage:
        reasons.append("Creator allocation is too high")

    if criteria.require_mint_authority_revoked:
        if checks.get("mint_authority_revoked") is not True:
            reasons.append("Mint authority is active or unavailable")
    if criteria.require_freeze_authority_revoked:
        if checks.get("freeze_authority_revoked") is not True:
            reasons.append("Freeze authority is active or unavailable")
    return list(dict.fromkeys(reasons))

