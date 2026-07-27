from typing import Any

import httpx


class SolanaCollector:
    def __init__(self, client: httpx.AsyncClient, rpc_url: str) -> None:
        self.client = client
        self.rpc_url = rpc_url
        self._request_id = 0

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        response = await self.client.post(
            self.rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            },
        )
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(body["error"].get("message", "Solana RPC error"))
        return body.get("result")

    async def get_token_checks(self, mint_address: str) -> dict[str, Any]:
        checks: dict[str, Any] = {
            "mint_authority_revoked": None,
            "freeze_authority_revoked": None,
            "top_10_holder_percentage": None,
            "creator_percentage": None,
        }
        try:
            account = await self._rpc(
                "getAccountInfo",
                [mint_address, {"encoding": "jsonParsed", "commitment": "confirmed"}],
            )
            parsed = ((account or {}).get("value") or {}).get("data", {}).get("parsed", {})
            info = parsed.get("info", {})
            if "mintAuthority" in info:
                checks["mint_authority_revoked"] = info["mintAuthority"] is None
            if "freezeAuthority" in info:
                checks["freeze_authority_revoked"] = info["freezeAuthority"] is None
            supply_raw = float(info.get("supply", 0))
            if supply_raw > 0:
                largest = await self._rpc(
                    "getTokenLargestAccounts",
                    [mint_address, {"commitment": "confirmed"}],
                )
                amounts = [
                    float(item.get("amount", 0))
                    for item in ((largest or {}).get("value") or [])[:10]
                ]
                checks["top_10_holder_percentage"] = round(
                    sum(amounts) / supply_raw * 100, 4
                )
        except (httpx.HTTPError, RuntimeError, TypeError, ValueError):
            pass
        return checks
