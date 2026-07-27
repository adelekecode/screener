from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.analysis.filters import apply_filters
from app.config import Criteria


def safe_candidate() -> dict:
    return {
        "pair_created_at": datetime.now(UTC) - timedelta(minutes=25),
        "liquidity_usd": 50_000,
        "market_cap_usd": 250_000,
        "volume_10m_usd": 15_000,
        "buys_10m": 80,
        "sells_10m": 30,
        "unique_buyers_10m": 35,
    }


def safe_checks() -> dict:
    return {
        "mint_authority_revoked": True,
        "freeze_authority_revoked": True,
        "top_10_holder_percentage": 20,
        "creator_percentage": 2,
    }


def test_safe_candidate_passes_filters() -> None:
    assert apply_filters(safe_candidate(), safe_checks(), Criteria()) == []


def test_unknown_required_checks_fail_closed() -> None:
    candidate = safe_candidate()
    candidate["unique_buyers_10m"] = None
    checks = safe_checks()
    checks["mint_authority_revoked"] = None
    checks["top_10_holder_percentage"] = None

    reasons = apply_filters(candidate, checks, Criteria())

    assert "Unique buyer count is unavailable" in reasons
    assert "Holder concentration is unavailable" in reasons
    assert "Mint authority is active or unavailable" in reasons


def test_zero_sells_is_rejected_even_with_many_buys() -> None:
    candidate = safe_candidate()
    candidate["sells_10m"] = 0

    reasons = apply_filters(candidate, safe_checks(), Criteria())

    assert "No recent selling activity" in reasons


def test_invalid_criteria_ranges_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Criteria(minimum_pair_age_minutes=60, maximum_pair_age_minutes=10)
