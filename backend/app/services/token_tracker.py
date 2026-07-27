import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.collectors.dexscreener import DexScreenerCollector
from app.database.models import Alert

logger = logging.getLogger(__name__)


class TokenTrackerService:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        dexscreener_base_url: str,
        session_factory: async_sessionmaker,
    ) -> None:
        self.collector = DexScreenerCollector(client, dexscreener_base_url)
        self.session_factory = session_factory

    async def update_alerted_tokens(self) -> int:
        updated = 0
        async with self.session_factory() as session:
            alerts = list(
                await session.scalars(
                    select(Alert)
                    .where(Alert.success.is_(True), Alert.initial_price_usd.is_not(None))
                    .order_by(Alert.sent_at.desc())
                    .limit(200)
                )
            )
            price_cache: dict[str, float | None] = {}
            for alert in alerts:
                try:
                    if alert.pair_address not in price_cache:
                        pair = await self.collector.get_pair(alert.pair_address)
                        price_cache[alert.pair_address] = pair.get("price_usd") if pair else None
                    price = price_cache[alert.pair_address]
                    if price is None or not alert.initial_price_usd:
                        continue
                    alert.current_price_usd = price
                    alert.maximum_price_usd = max(alert.maximum_price_usd or price, price)
                    alert.minimum_price_usd = min(alert.minimum_price_usd or price, price)
                    alert.maximum_gain_percentage = round(
                        (alert.maximum_price_usd / alert.initial_price_usd - 1) * 100, 2
                    )
                    alert.maximum_decline_percentage = round(
                        (alert.minimum_price_usd / alert.initial_price_usd - 1) * 100, 2
                    )
                    alert.last_tracked_at = datetime.now(UTC)
                    updated += 1
                except (httpx.HTTPError, TypeError, ValueError):
                    logger.warning("Unable to track pair %s", alert.pair_address)
            await session.commit()
        return updated
