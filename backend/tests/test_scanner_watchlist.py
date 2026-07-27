import time

import pytest

from app.config import Settings
from app.services.scanner import ScannerService


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, float] = {}

    async def zadd(
        self, _name: str, mapping: dict[str, float], *, nx: bool = False
    ) -> None:
        for member, score in mapping.items():
            if not nx or member not in self.values:
                self.values[member] = score

    async def zrangebyscore(
        self, _name: str, minimum: float, _maximum: str
    ) -> list[str]:
        return [
            member
            for member, score in self.values.items()
            if score >= float(minimum)
        ]

    async def zremrangebyscore(
        self, _name: str, _minimum: str, maximum: float
    ) -> None:
        self.values = {
            member: score
            for member, score in self.values.items()
            if score > float(maximum)
        }


@pytest.mark.asyncio
async def test_watchlist_keeps_active_tokens_and_removes_expired_tokens() -> None:
    scanner = ScannerService.__new__(ScannerService)
    scanner.redis = FakeRedis()
    scanner.settings = Settings(scan_interval_minutes=10)
    now = time.time()
    scanner.redis.values = {
        "still-watched": now + 600,
        "expired": now - 1,
    }

    tokens = await scanner._tokens_for_scan(["new-token"], watch_minutes=60)

    assert tokens == ["new-token", "still-watched"]
    assert "expired" not in scanner.redis.values
    assert scanner.redis.values["new-token"] > now


@pytest.mark.asyncio
async def test_rediscovery_does_not_extend_original_watch_window() -> None:
    scanner = ScannerService.__new__(ScannerService)
    scanner.redis = FakeRedis()
    scanner.settings = Settings(scan_interval_minutes=10)
    original_expiry = time.time() + 300
    scanner.redis.values = {"known-token": original_expiry}

    await scanner._tokens_for_scan(["known-token"], watch_minutes=60)

    assert scanner.redis.values["known-token"] == original_expiry

