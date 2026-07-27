from datetime import UTC, datetime
from typing import Any

import httpx


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


class DexScreenerCollector:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")

    async def discover_solana_tokens(self) -> list[str]:
        response = await self.client.get(f"{self.base_url}/token-profiles/latest/v1")
        response.raise_for_status()
        profiles = response.json()
        return list(
            dict.fromkeys(
                profile["tokenAddress"]
                for profile in profiles
                if profile.get("chainId") == "solana" and profile.get("tokenAddress")
            )
        )

    async def get_pairs(self, token_address: str) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.base_url}/token-pairs/v1/solana/{token_address}"
        )
        response.raise_for_status()
        pairs = response.json()
        return [self.normalize_pair(pair) for pair in pairs if pair.get("chainId") == "solana"]

    async def get_pair(self, pair_address: str) -> dict[str, Any] | None:
        response = await self.client.get(
            f"{self.base_url}/latest/dex/pairs/solana/{pair_address}"
        )
        response.raise_for_status()
        pairs = response.json().get("pairs") or []
        return self.normalize_pair(pairs[0]) if pairs else None

    @staticmethod
    def normalize_pair(pair: dict[str, Any]) -> dict[str, Any]:
        txns_5m = pair.get("txns", {}).get("m5", {})
        volume_5m = _number(pair.get("volume", {}).get("m5"))
        created_ms = _integer(pair.get("pairCreatedAt"))
        pair_created_at = (
            datetime.fromtimestamp(created_ms / 1000, tz=UTC) if created_ms else None
        )
        base_token = pair.get("baseToken") or {}
        info = pair.get("info") or {}
        return {
            "pair_address": pair.get("pairAddress"),
            "token_address": base_token.get("address"),
            "chain_id": pair.get("chainId", "solana"),
            "dex_id": pair.get("dexId"),
            "symbol": base_token.get("symbol") or "UNKNOWN",
            "name": base_token.get("name") or "Unknown",
            "price_usd": _number(pair.get("priceUsd")),
            "market_cap_usd": _number(pair.get("marketCap") or pair.get("fdv")),
            "liquidity_usd": _number(pair.get("liquidity", {}).get("usd")),
            "volume_5m_usd": volume_5m,
            "volume_1h_usd": _number(pair.get("volume", {}).get("h1")),
            # DEX Screener has no 10-minute bucket. The current 5-minute bucket is
            # used as a conservative lower bound and is explicitly marked below.
            "volume_10m_usd": volume_5m,
            "buys_5m": _integer(txns_5m.get("buys")),
            "sells_5m": _integer(txns_5m.get("sells")),
            "buys_10m": _integer(txns_5m.get("buys")),
            "sells_10m": _integer(txns_5m.get("sells")),
            "unique_buyers_10m": None,
            "pair_created_at": pair_created_at,
            "socials": info.get("socials") or [],
            "websites": info.get("websites") or [],
            "url": pair.get("url"),
            "raw_data": pair,
            "data_notes": [
                "volume_10m_usd and 10m transactions use the current 5m bucket as a lower bound",
                "unique buyer count is unavailable from DEX Screener",
            ],
        }
