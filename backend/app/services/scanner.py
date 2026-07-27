import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.analysis.filters import apply_filters
from app.analysis.risk_checks import build_risk_flags
from app.analysis.scoring import score_candidate
from app.collectors.dexscreener import DexScreenerCollector
from app.collectors.solana import SolanaCollector
from app.config import Settings
from app.database import repositories
from app.database.models import Opportunity
from app.notifications.discord import DiscordNotifier

logger = logging.getLogger(__name__)


class ScannerService:
    lock_key = "scanner:scan-lock"
    paused_key = "scanner:paused"

    def __init__(
        self,
        *,
        settings: Settings,
        redis: Redis,
        session_factory: async_sessionmaker,
        http_client: httpx.AsyncClient,
    ) -> None:
        self.settings = settings
        self.redis = redis
        self.session_factory = session_factory
        self.dexscreener = DexScreenerCollector(http_client, settings.dexscreener_base_url)
        self.solana = SolanaCollector(http_client, settings.solana_rpc_url)
        self.notifier = DiscordNotifier(http_client, settings.discord_webhook_url)
        self.current_task: asyncio.Task[None] | None = None

    async def is_paused(self) -> bool:
        return bool(await self.redis.exists(self.paused_key))

    async def pause(self) -> None:
        await self.redis.set(self.paused_key, "1")

    async def resume(self) -> None:
        await self.redis.delete(self.paused_key)

    def start_scan(self) -> bool:
        if self.current_task and not self.current_task.done():
            return False
        self.current_task = asyncio.create_task(self.run_scan(), name="manual-memecoin-scan")
        return True

    async def run_scan(self) -> None:
        if await self.is_paused():
            logger.info("Scanner is paused; skipping scheduled scan")
            return
        lock_token = str(uuid.uuid4())
        acquired = await self.redis.set(
            self.lock_key,
            lock_token,
            ex=self.settings.redis_lock_ttl_seconds,
            nx=True,
        )
        if not acquired:
            logger.info("A scan already holds the Redis lock")
            return

        discovered_count = processed_count = qualified_count = alerted_count = 0
        scan = None
        try:
            async with self.session_factory() as session:
                scan = await repositories.create_scan(session)
                criteria_overrides = await repositories.get_setting(
                    session, "criteria", default={}
                )
                criteria = self.settings.load_criteria(criteria_overrides)
                tokens = await self.dexscreener.discover_solana_tokens()
                discovered_count = len(tokens)

                candidates = await self._collect_candidates(tokens)
                candidates = await self._filter_unprocessed(candidates)
                checks_by_pair = await self._run_checks(candidates)

                for candidate in candidates:
                    pair_address = candidate["pair_address"]
                    checks = checks_by_pair[pair_address]
                    rejection_reasons = apply_filters(candidate, checks, criteria)
                    score, breakdown = score_candidate(candidate, checks, criteria)
                    risk_flags = build_risk_flags(checks)
                    qualified = (
                        not rejection_reasons
                        and score >= criteria.minimum_score_for_alert
                    )
                    if score < criteria.minimum_score_for_alert:
                        rejection_reasons.append("Score is below the alert threshold")

                    db_values = self._database_values(
                        candidate,
                        checks=checks,
                        score=score,
                        score_breakdown=breakdown,
                        risk_flags=risk_flags,
                        rejection_reasons=rejection_reasons,
                        qualified=qualified,
                    )
                    opportunity = await repositories.upsert_opportunity(
                        session, db_values
                    )
                    processed_count += 1
                    await self.redis.set(
                        f"processed:{pair_address}",
                        "1",
                        ex=self.settings.processed_ttl_seconds,
                    )

                    if qualified:
                        qualified_count += 1
                        alert_key = f"alerted:{pair_address}"
                        if not await self.redis.exists(alert_key):
                            result = await self.notifier.send(
                                self._opportunity_dict(opportunity)
                            )
                            await repositories.save_alert(
                                session,
                                pair_address=pair_address,
                                success=result.success,
                                status_code=result.status_code,
                                error=result.error,
                                payload=result.payload,
                                initial_price_usd=opportunity.price_usd,
                            )
                            if result.success:
                                alerted_count += 1
                                await self.redis.set(
                                    alert_key,
                                    "1",
                                    ex=self.settings.processed_ttl_seconds,
                                )

                await repositories.finish_scan(
                    session,
                    scan,
                    status="completed",
                    discovered_count=discovered_count,
                    processed_count=processed_count,
                    qualified_count=qualified_count,
                    alerted_count=alerted_count,
                )
        except Exception as exc:
            logger.exception("Scan failed")
            if scan is not None:
                async with self.session_factory() as error_session:
                    persistent_scan = await error_session.get(type(scan), scan.id)
                    if persistent_scan:
                        await repositories.finish_scan(
                            error_session,
                            persistent_scan,
                            status="failed",
                            discovered_count=discovered_count,
                            processed_count=processed_count,
                            qualified_count=qualified_count,
                            alerted_count=alerted_count,
                            error=str(exc)[:2000],
                        )
        finally:
            await self.redis.eval(
                """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                end
                return 0
                """,
                1,
                self.lock_key,
                lock_token,
            )

    async def _gather_bounded(self, coros: list[Any], limit: int) -> list[Any]:
        semaphore = asyncio.Semaphore(limit)

        async def run(coro: Any) -> Any:
            async with semaphore:
                return await coro

        return await asyncio.gather(*(run(coro) for coro in coros), return_exceptions=True)

    async def _collect_candidates(self, tokens: list[str]) -> list[dict[str, Any]]:
        results = await self._gather_bounded(
            [self.dexscreener.get_pairs(token) for token in tokens],
            self.settings.scan_concurrency,
        )
        candidates: dict[str, dict[str, Any]] = {}
        for token, result in zip(tokens, results):
            if isinstance(result, BaseException):
                logger.warning("Failed to fetch pairs for %s: %s", token, result)
                continue
            for candidate in result:
                pair_address = candidate.get("pair_address")
                if pair_address and pair_address not in candidates:
                    candidates[pair_address] = candidate
        return list(candidates.values())

    async def _filter_unprocessed(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not candidates:
            return []
        pipeline = self.redis.pipeline()
        for candidate in candidates:
            pipeline.exists(f"processed:{candidate['pair_address']}")
        already_processed = await pipeline.execute()
        return [
            candidate
            for candidate, processed in zip(candidates, already_processed)
            if not processed
        ]

    async def _run_checks(
        self, candidates: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        results = await self._gather_bounded(
            [self.solana.get_token_checks(c["token_address"]) for c in candidates],
            self.settings.scan_concurrency,
        )
        checks_by_pair: dict[str, dict[str, Any]] = {}
        for candidate, result in zip(candidates, results):
            pair_address = candidate["pair_address"]
            if isinstance(result, BaseException):
                logger.warning("Risk check failed for %s: %s", pair_address, result)
                result = {}
            checks = dict(result)
            checks["unique_buyers_10m"] = candidate.get("unique_buyers_10m")
            checks_by_pair[pair_address] = checks
        return checks_by_pair

    @staticmethod
    def _database_values(
        candidate: dict[str, Any],
        *,
        checks: dict[str, Any],
        score: int,
        score_breakdown: dict[str, Any],
        risk_flags: list[str],
        rejection_reasons: list[str],
        qualified: bool,
    ) -> dict[str, Any]:
        columns = {
            "pair_address",
            "token_address",
            "chain_id",
            "dex_id",
            "symbol",
            "name",
            "price_usd",
            "market_cap_usd",
            "liquidity_usd",
            "volume_5m_usd",
            "volume_1h_usd",
            "volume_10m_usd",
            "buys_5m",
            "sells_5m",
            "buys_10m",
            "sells_10m",
            "unique_buyers_10m",
            "pair_created_at",
            "raw_data",
        }
        values = {key: candidate.get(key) for key in columns}
        values.update(
            {
                "checks": checks,
                "score": score,
                "score_breakdown": score_breakdown,
                "risk_flags": risk_flags,
                "rejection_reasons": rejection_reasons,
                "qualified": qualified,
            }
        )
        return values

    @staticmethod
    def _opportunity_dict(opportunity: Opportunity) -> dict[str, Any]:
        return {
            column.name: getattr(opportunity, column.name)
            for column in Opportunity.__table__.columns
        }
