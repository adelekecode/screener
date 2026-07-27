from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import repositories
from app.database.session import get_session
from app.schemas import AlertRead, OpportunityRead

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[OpportunityRead])
async def opportunities(
    session: Session,
    qualified: bool | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    scan_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[OpportunityRead]:
    return await repositories.list_opportunities(
        session,
        qualified=qualified,
        min_score=min_score,
        scan_id=scan_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{pair_address}", response_model=OpportunityRead)
async def opportunity(pair_address: str, session: Session) -> OpportunityRead:
    item = await repositories.get_opportunity(session, pair_address)
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return item


@router.post("/{pair_address}/send-to-discord", response_model=AlertRead)
async def send_to_discord(
    pair_address: str,
    request: Request,
    session: Session,
) -> AlertRead:
    item = await repositories.get_opportunity(session, pair_address)
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    scanner = request.app.state.scanner
    result = await scanner.notifier.send(
        scanner._opportunity_dict(item),
        manual=True,
    )
    alert = await repositories.save_alert(
        session,
        pair_address=pair_address,
        success=result.success,
        status_code=result.status_code,
        error=result.error,
        payload=result.payload,
        initial_price_usd=item.price_usd,
    )
    if not result.success:
        raise HTTPException(
            status_code=502,
            detail={"message": "Discord delivery failed", "error": result.error},
        )

    await scanner.redis.set(
        f"alerted:{pair_address}",
        "1",
        ex=scanner.settings.processed_ttl_seconds,
    )
    return alert
