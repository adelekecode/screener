from datetime import UTC, datetime, timedelta

from app.analysis.scoring import score_candidate
from app.config import Criteria


def test_scoring_is_bounded_and_breakdown_totals_to_score() -> None:
    criteria = Criteria()
    candidate = {
        "pair_created_at": datetime.now(UTC) - timedelta(minutes=35),
        "liquidity_usd": 100_000_000,
        "volume_10m_usd": 100_000_000,
        "buys_10m": 1000,
        "sells_10m": 100,
        "socials": [{"type": "twitter", "url": "https://example.test"}],
    }
    checks = {
        "mint_authority_revoked": True,
        "freeze_authority_revoked": True,
        "top_10_holder_percentage": 0,
    }

    score, breakdown = score_candidate(candidate, checks, criteria)

    assert 0 <= score <= 100
    assert score == round(sum(breakdown.values()))
    assert set(breakdown) == {
        "liquidity",
        "volume_and_momentum",
        "buy_sell_activity",
        "holder_distribution",
        "token_permissions",
        "pair_maturity",
        "social_information",
    }


def test_unknown_chain_checks_receive_no_safety_points() -> None:
    criteria = Criteria()
    candidate = {
        "pair_created_at": datetime.now(UTC) - timedelta(minutes=30),
        "liquidity_usd": 40_000,
        "volume_10m_usd": 10_000,
        "buys_10m": 60,
        "sells_10m": 20,
    }

    _, breakdown = score_candidate(candidate, {}, criteria)

    assert breakdown["holder_distribution"] == 0
    assert breakdown["token_permissions"] == 0

