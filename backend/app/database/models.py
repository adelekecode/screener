import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    qualified_count: Mapped[int] = mapped_column(Integer, default=0)
    alerted_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class Opportunity(Base):
    __tablename__ = "opportunities"

    pair_address: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    chain_id: Mapped[str] = mapped_column(String(32), default="solana")
    dex_id: Mapped[str | None] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    name: Mapped[str] = mapped_column(String(128), default="Unknown")
    price_usd: Mapped[float | None] = mapped_column(Float)
    market_cap_usd: Mapped[float | None] = mapped_column(Float)
    liquidity_usd: Mapped[float | None] = mapped_column(Float)
    volume_5m_usd: Mapped[float | None] = mapped_column(Float)
    volume_1h_usd: Mapped[float | None] = mapped_column(Float)
    volume_10m_usd: Mapped[float | None] = mapped_column(Float)
    buys_5m: Mapped[int | None] = mapped_column(Integer)
    sells_5m: Mapped[int | None] = mapped_column(Integer)
    buys_10m: Mapped[int | None] = mapped_column(Integer)
    sells_10m: Mapped[int | None] = mapped_column(Integer)
    unique_buyers_10m: Mapped[int | None] = mapped_column(Integer)
    pair_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    qualified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rejection_reasons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    checks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="opportunity")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_address: Mapped[str] = mapped_column(
        ForeignKey("opportunities.pair_address"), index=True
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    initial_price_usd: Mapped[float | None] = mapped_column(Float)
    current_price_usd: Mapped[float | None] = mapped_column(Float)
    maximum_price_usd: Mapped[float | None] = mapped_column(Float)
    minimum_price_usd: Mapped[float | None] = mapped_column(Float)
    maximum_gain_percentage: Mapped[float | None] = mapped_column(Float)
    maximum_decline_percentage: Mapped[float | None] = mapped_column(Float)
    last_tracked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opportunity: Mapped[Opportunity] = relationship(back_populates="alerts")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
