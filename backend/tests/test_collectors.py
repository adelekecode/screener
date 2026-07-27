from datetime import UTC, datetime

from app.collectors.dexscreener import DexScreenerCollector


def test_normalize_pair_maps_dexscreener_fields() -> None:
    created_ms = int(datetime.now(UTC).timestamp() * 1000)
    pair = {
        "chainId": "solana",
        "dexId": "raydium",
        "pairAddress": "pair",
        "baseToken": {"address": "mint", "name": "Example", "symbol": "EX"},
        "priceUsd": "0.001",
        "marketCap": 100_000,
        "liquidity": {"usd": 25_000},
        "volume": {"m5": 7_500, "h1": 30_000},
        "txns": {"m5": {"buys": 40, "sells": 15}},
        "pairCreatedAt": created_ms,
    }

    normalized = DexScreenerCollector.normalize_pair(pair)

    assert normalized["pair_address"] == "pair"
    assert normalized["token_address"] == "mint"
    assert normalized["price_usd"] == 0.001
    assert normalized["volume_10m_usd"] == 7_500
    assert normalized["buys_10m"] == 40
    assert normalized["unique_buyers_10m"] is None
    assert normalized["pair_created_at"].tzinfo is not None

