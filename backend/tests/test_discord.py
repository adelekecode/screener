from app.notifications.discord import DiscordNotifier


def test_discord_payload_contains_safety_disclaimer_and_links() -> None:
    payload = DiscordNotifier.build_payload(
        {
            "score": 78,
            "symbol": "EX",
            "market_cap_usd": 184_000,
            "liquidity_usd": 38_500,
            "volume_10m_usd": 16_200,
            "buys_10m": 86,
            "sells_10m": 31,
            "token_address": "mint",
            "pair_address": "pair",
            "checks": {
                "mint_authority_revoked": True,
                "freeze_authority_revoked": True,
            },
            "risk_flags": [],
        }
    )

    assert "78/100" in payload["content"]
    assert "not a buy signal" in payload["content"]
    assert "dexscreener.com/solana/pair" in payload["content"]
    assert len(payload["content"]) <= 2000


def test_manual_discord_payload_is_clearly_labelled() -> None:
    payload = DiscordNotifier.build_payload(
        {
            "score": 72,
            "symbol": "WATCH",
            "token_address": "mint",
            "pair_address": "pair",
        },
        manual=True,
    )

    assert "MANUAL MONITOR" in payload["content"]
    assert "automatic safety criteria may not have passed" in payload["content"]
