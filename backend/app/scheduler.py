from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.scanner import ScannerService
from app.services.token_tracker import TokenTrackerService


def build_scheduler(
    scanner: ScannerService,
    tracker: TokenTrackerService,
    interval_minutes: int,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        scanner.run_scan,
        trigger="interval",
        minutes=interval_minutes,
        id="memecoin-scan",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        tracker.update_alerted_tokens,
        trigger="interval",
        minutes=interval_minutes,
        id="token-tracker",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    return scheduler
