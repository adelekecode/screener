from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class NotificationResult:
    success: bool
    status_code: int | None
    error: str | None
    payload: dict[str, Any]


class DiscordNotifier:
    def __init__(self, client: httpx.AsyncClient, webhook_url: str | None) -> None:
        self.client = client
        self.webhook_url = webhook_url

    @staticmethod
    def build_payload(opportunity: dict[str, Any]) -> dict[str, str]:
        checks = opportunity.get("checks") or {}
        flags = opportunity.get("risk_flags") or []
        buys = opportunity.get("buys_10m")
        sells = opportunity.get("sells_10m")
        token = opportunity.get("token_address", "")
        pair = opportunity.get("pair_address", "")
        symbol = opportunity.get("symbol", "UNKNOWN")
        lines = [
            f"🟡 **NEW TOKEN OPPORTUNITY — SCORE {opportunity.get('score', 0)}/100**",
            "",
            f"**Token:** {symbol}",
            f"**Market cap:** ${opportunity.get('market_cap_usd') or 0:,.0f}",
            f"**Liquidity:** ${opportunity.get('liquidity_usd') or 0:,.0f}",
            f"**Recent volume (5m lower bound):** ${opportunity.get('volume_10m_usd') or 0:,.0f}",
            f"**Buys/Sells (5m):** {buys if buys is not None else '?'} / "
            f"{sells if sells is not None else '?'}",
            "",
            "✅ Mint authority revoked"
            if checks.get("mint_authority_revoked") is True
            else "❓ Mint authority not verified",
            "✅ Freeze authority revoked"
            if checks.get("freeze_authority_revoked") is True
            else "❓ Freeze authority not verified",
        ]
        lines.extend(f"⚠️ {flag}" for flag in flags[:5])
        lines.extend(
            [
                "",
                f"**Contract:** `{token}`",
                f"[DEX Screener](https://dexscreener.com/solana/{pair}) · "
                f"[Solscan](https://solscan.io/token/{token}) · "
                f"[Jupiter](https://jup.ag/swap/SOL-{token})",
                "",
                "_Research manually before trading. This is not a buy signal._",
            ]
        )
        return {"content": "\n".join(lines)[:2000]}

    async def send(
        self, opportunity: dict[str, Any], payload: dict[str, Any] | None = None
    ) -> NotificationResult:
        message = payload or self.build_payload(opportunity)
        if not self.webhook_url:
            return NotificationResult(False, None, "Discord webhook is not configured", message)
        try:
            response = await self.client.post(self.webhook_url, json=message)
            response.raise_for_status()
            return NotificationResult(True, response.status_code, None, message)
        except httpx.HTTPStatusError as exc:
            return NotificationResult(
                False, exc.response.status_code, str(exc), message
            )
        except httpx.HTTPError as exc:
            return NotificationResult(False, None, str(exc), message)

