from datetime import UTC, datetime
from typing import Any

from app.config import Criteria


def _ratio(value: float | int | None, target: float | int) -> float:
    if value is None or target <= 0:
        return 0.0
    return min(max(float(value) / float(target), 0.0), 1.0)


def score_candidate(
    candidate: dict[str, Any], checks: dict[str, Any], criteria: Criteria
) -> tuple[int, dict[str, float]]:
    liquidity = 20 * _ratio(candidate.get("liquidity_usd"), criteria.minimum_liquidity_usd * 2)
    momentum = 20 * _ratio(
        candidate.get("volume_10m_usd"), criteria.minimum_volume_10m_usd * 2
    )

    buys = candidate.get("buys_10m") or 0
    sells = candidate.get("sells_10m") or 0
    buy_sell_ratio = buys / sells if sells else 0
    activity = 15 * (
        0.6 * _ratio(buys, criteria.minimum_buys_10m * 2)
        + 0.4 * _ratio(buy_sell_ratio, criteria.minimum_buy_sell_ratio * 1.5)
    )

    top_10 = checks.get("top_10_holder_percentage")
    holders = (
        20 * max(0.0, 1 - top_10 / criteria.maximum_top_10_holder_percentage)
        if top_10 is not None and criteria.maximum_top_10_holder_percentage
        else 0.0
    )
    permissions = 7.5 * float(checks.get("mint_authority_revoked") is True)
    permissions += 7.5 * float(checks.get("freeze_authority_revoked") is True)

    created_at = candidate.get("pair_created_at")
    maturity = 0.0
    if created_at:
        age = (datetime.now(UTC) - created_at).total_seconds() / 60
        if criteria.minimum_pair_age_minutes <= age <= criteria.maximum_pair_age_minutes:
            midpoint = (
                criteria.minimum_pair_age_minutes + criteria.maximum_pair_age_minutes
            ) / 2
            span = max(criteria.maximum_pair_age_minutes - criteria.minimum_pair_age_minutes, 1)
            maturity = 5 * max(0.0, 1 - abs(age - midpoint) / span)

    social = 5.0 if candidate.get("socials") or candidate.get("websites") else 0.0
    breakdown = {
        "liquidity": round(liquidity, 2),
        "volume_and_momentum": round(momentum, 2),
        "buy_sell_activity": round(activity, 2),
        "holder_distribution": round(holders, 2),
        "token_permissions": round(permissions, 2),
        "pair_maturity": round(maturity, 2),
        "social_information": round(social, 2),
    }
    return min(round(sum(breakdown.values())), 100), breakdown

