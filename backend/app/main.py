import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api import alerts, health, opportunities, scans, settings as settings_api
from app.config import get_settings
from app.database import repositories
from app.database.session import SessionLocal
from app.scheduler import build_scheduler
from app.services.scanner import ScannerService
from app.services.token_tracker import TokenTrackerService

app_settings = get_settings()
logging.basicConfig(
    level=getattr(logging, app_settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(app_settings.redis_url, decode_responses=True)
    http_client = httpx.AsyncClient(timeout=app_settings.request_timeout_seconds)

    async with SessionLocal() as session:
        interval = await repositories.get_setting(
            session, "scan_interval_minutes", app_settings.scan_interval_minutes
        )
        webhook = await repositories.get_setting(
            session, "discord_webhook_url", app_settings.discord_webhook_url
        )

    scanner = ScannerService(
        settings=app_settings,
        redis=redis,
        session_factory=SessionLocal,
        http_client=http_client,
    )
    scanner.notifier.webhook_url = webhook
    tracker = TokenTrackerService(
        client=http_client,
        dexscreener_base_url=app_settings.dexscreener_base_url,
        session_factory=SessionLocal,
    )
    scheduler = build_scheduler(scanner, tracker, interval)
    app.state.redis = redis
    app.state.scanner = scanner
    app.state.tracker = tracker
    app.state.scheduler = scheduler
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        if scanner.current_task and not scanner.current_task.done():
            scanner.current_task.cancel()
        await http_client.aclose()
        await redis.aclose()


app = FastAPI(
    title="Screener",
    description=(
        "A local Solana token research and alerting assistant. "
        "It does not connect to wallets or execute trades."
    ),
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(opportunities.router)
app.include_router(alerts.router)
app.include_router(scans.router)
app.include_router(settings_api.router)
