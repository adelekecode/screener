from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OpportunityRead(ORMModel):
    pair_address: str
    token_address: str
    chain_id: str
    dex_id: str | None
    symbol: str
    name: str
    price_usd: float | None
    market_cap_usd: float | None
    liquidity_usd: float | None
    volume_5m_usd: float | None
    volume_1h_usd: float | None
    volume_10m_usd: float | None
    buys_5m: int | None
    sells_5m: int | None
    buys_10m: int | None
    sells_10m: int | None
    unique_buyers_10m: int | None
    pair_created_at: datetime | None
    score: int
    qualified: bool
    rejection_reasons: list[str]
    risk_flags: list[str]
    checks: dict[str, Any]
    score_breakdown: dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime
    last_scan_id: UUID | None


class ScanRead(ORMModel):
    id: UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    discovered_count: int
    processed_count: int
    qualified_count: int
    alerted_count: int
    error: str | None


class AlertRead(ORMModel):
    id: UUID
    pair_address: str
    sent_at: datetime
    success: bool
    status_code: int | None
    error: str | None
    payload: dict[str, Any]
    initial_price_usd: float | None
    current_price_usd: float | None
    maximum_price_usd: float | None
    minimum_price_usd: float | None
    maximum_gain_percentage: float | None
    maximum_decline_percentage: float | None
    last_tracked_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    scanner: str


class StatsRead(BaseModel):
    opportunities: int
    qualified: int
    alerts_today: int
    scans: int
    last_scan: ScanRead | None = None
    next_scan_at: datetime | None = None
    scanner_paused: bool


class SettingsRead(BaseModel):
    criteria: dict[str, Any]
    scan_interval_minutes: int
    scanner_paused: bool
    discord_configured: bool


class SettingsPatch(BaseModel):
    criteria: dict[str, Any] | None = None
    scan_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    discord_webhook_url: str | None = None
