from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Alert, AppSetting, Opportunity, Scan


async def create_scan(session: AsyncSession) -> Scan:
    scan = Scan()
    session.add(scan)
    await session.commit()
    await session.refresh(scan)
    return scan


async def finish_scan(
    session: AsyncSession,
    scan: Scan,
    *,
    status: str,
    discovered_count: int = 0,
    processed_count: int = 0,
    qualified_count: int = 0,
    alerted_count: int = 0,
    error: str | None = None,
) -> Scan:
    scan.status = status
    scan.finished_at = datetime.now(UTC)
    scan.discovered_count = discovered_count
    scan.processed_count = processed_count
    scan.qualified_count = qualified_count
    scan.alerted_count = alerted_count
    scan.error = error
    await session.commit()
    await session.refresh(scan)
    return scan


async def upsert_opportunity(session: AsyncSession, values: dict[str, Any]) -> Opportunity:
    values["last_seen_at"] = datetime.now(UTC)
    statement = insert(Opportunity).values(**values)
    update_values = {
        key: getattr(statement.excluded, key)
        for key in values
        if key not in {"pair_address", "first_seen_at"}
    }
    statement = statement.on_conflict_do_update(
        index_elements=[Opportunity.pair_address], set_=update_values
    ).returning(Opportunity)
    opportunity = (await session.execute(statement)).scalar_one()
    await session.commit()
    return opportunity


async def delete_below_score_without_alerts(
    session: AsyncSession,
    minimum_score: int,
    *,
    current_below_threshold: list[str] | None = None,
) -> int:
    has_alert = (
        select(Alert.id)
        .where(Alert.pair_address == Opportunity.pair_address)
        .exists()
    )
    below_threshold = [Opportunity.score < minimum_score]
    if current_below_threshold:
        below_threshold.append(
            Opportunity.pair_address.in_(current_below_threshold)
        )
    result = await session.execute(
        delete(Opportunity).where(
            or_(*below_threshold),
            ~has_alert,
        )
    )
    await session.commit()
    return result.rowcount or 0


def _opportunity_query(
    *,
    qualified: bool | None = None,
    min_score: int | None = None,
    scan_id: UUID | None = None,
) -> Select[tuple[Opportunity]]:
    query = select(Opportunity)
    if qualified is not None:
        query = query.where(Opportunity.qualified.is_(qualified))
    if min_score is not None:
        query = query.where(Opportunity.score >= min_score)
    if scan_id is not None:
        query = query.where(Opportunity.last_scan_id == scan_id)
    return query.order_by(Opportunity.last_seen_at.desc())


async def list_opportunities(
    session: AsyncSession,
    *,
    qualified: bool | None = None,
    min_score: int | None = None,
    scan_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Opportunity]:
    query = _opportunity_query(qualified=qualified, min_score=min_score, scan_id=scan_id)
    result = await session.scalars(query.limit(limit).offset(offset))
    return list(result)


async def get_opportunity(session: AsyncSession, pair_address: str) -> Opportunity | None:
    return await session.get(Opportunity, pair_address)


async def list_scans(session: AsyncSession, limit: int = 100) -> list[Scan]:
    result = await session.scalars(
        select(Scan).order_by(Scan.started_at.desc()).limit(limit)
    )
    return list(result)


async def list_alerts(session: AsyncSession, limit: int = 100) -> list[Alert]:
    result = await session.scalars(
        select(Alert).order_by(Alert.sent_at.desc()).limit(limit)
    )
    return list(result)


async def get_alert(session: AsyncSession, alert_id: UUID) -> Alert | None:
    return await session.get(Alert, alert_id)


async def save_alert(
    session: AsyncSession,
    *,
    pair_address: str,
    success: bool,
    status_code: int | None,
    error: str | None,
    payload: dict[str, Any],
    initial_price_usd: float | None = None,
) -> Alert:
    alert = Alert(
        pair_address=pair_address,
        success=success,
        status_code=status_code,
        error=error,
        payload=payload,
        initial_price_usd=initial_price_usd,
        current_price_usd=initial_price_usd,
        maximum_price_usd=initial_price_usd,
        minimum_price_usd=initial_price_usd,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_setting(session: AsyncSession, key: str, default: Any = None) -> Any:
    setting = await session.get(AppSetting, key)
    return setting.value if setting else default


async def set_setting(session: AsyncSession, key: str, value: Any) -> None:
    statement = insert(AppSetting).values(key=key, value=value)
    statement = statement.on_conflict_do_update(
        index_elements=[AppSetting.key],
        set_={"value": statement.excluded.value, "updated_at": func.now()},
    )
    await session.execute(statement)
    await session.commit()


async def get_stats(session: AsyncSession) -> dict[str, Any]:
    now = datetime.now(UTC)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    opportunities = await session.scalar(select(func.count()).select_from(Opportunity))
    qualified = await session.scalar(
        select(func.count()).select_from(Opportunity).where(Opportunity.qualified.is_(True))
    )
    alerts_today = await session.scalar(
        select(func.count())
        .select_from(Alert)
        .where(Alert.success.is_(True), Alert.sent_at >= start_of_day)
    )
    scans = await session.scalar(select(func.count()).select_from(Scan))
    last_scan = await session.scalar(select(Scan).order_by(Scan.started_at.desc()).limit(1))
    return {
        "opportunities": opportunities or 0,
        "qualified": qualified or 0,
        "alerts_today": alerts_today or 0,
        "scans": scans or 0,
        "last_scan": last_scan,
    }
