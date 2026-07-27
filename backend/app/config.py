from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Criteria(BaseModel):
    chain: str = "solana"
    maximum_pair_age_minutes: int = Field(default=60, ge=1)
    minimum_pair_age_minutes: int = Field(default=10, ge=0)
    minimum_liquidity_usd: float = Field(default=20_000, ge=0)
    maximum_market_cap_usd: float = Field(default=2_000_000, ge=0)
    minimum_market_cap_usd: float = Field(default=50_000, ge=0)
    minimum_volume_10m_usd: float = Field(default=5_000, ge=0)
    minimum_buys_10m: int = Field(default=30, ge=0)
    minimum_unique_buyers_10m: int = Field(default=15, ge=0)
    minimum_buy_sell_ratio: float = Field(default=1.5, ge=0)
    maximum_top_10_holder_percentage: float = Field(default=30, ge=0, le=100)
    maximum_creator_percentage: float = Field(default=5, ge=0, le=100)
    require_mint_authority_revoked: bool = True
    require_freeze_authority_revoked: bool = True
    minimum_score_for_alert: int = Field(default=70, ge=0, le=100)

    @model_validator(mode="after")
    def validate_ranges(self) -> "Criteria":
        if self.minimum_pair_age_minutes > self.maximum_pair_age_minutes:
            raise ValueError("minimum pair age cannot exceed maximum pair age")
        if self.minimum_market_cap_usd > self.maximum_market_cap_usd:
            raise ValueError("minimum market cap cannot exceed maximum market cap")
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Screener"
    database_url: str = (
        "postgresql+asyncpg://scanner:change-me@localhost:5432/memecoin_scanner"
    )
    redis_url: str = "redis://localhost:6379/0"
    dexscreener_base_url: str = "https://api.dexscreener.com"
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    discord_webhook_url: str | None = None
    scan_interval_minutes: int = Field(default=10, ge=1)
    criteria_path: Path = Path("config/criteria.yaml")
    request_timeout_seconds: float = Field(default=20, gt=0)
    scan_concurrency: int = Field(default=8, ge=1)
    redis_lock_ttl_seconds: int = Field(default=900, ge=30)
    processed_ttl_seconds: int = Field(default=86_400, ge=60)
    log_level: str = "INFO"

    def load_criteria(self, overrides: dict[str, Any] | None = None) -> Criteria:
        path = self.criteria_path
        if not path.exists():
            project_path = Path(__file__).resolve().parents[2] / "config" / "criteria.yaml"
            path = project_path
        raw = yaml.safe_load(path.read_text()) if path.exists() else {}
        return Criteria.model_validate({**(raw or {}), **(overrides or {})})


@lru_cache
def get_settings() -> Settings:
    return Settings()
