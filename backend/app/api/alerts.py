from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import repositories
from app.database.session import get_session
from app.schemas import AlertRead

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[AlertRead])
async def alerts(
    session: Session, limit: int = Query(default=100, ge=1, le=500)
) -> list[AlertRead]:
    return await repositories.list_alerts(session, limit=limit)


@router.post("/{alert_id}/resend", response_model=AlertRead)
async def resend_alert(alert_id: UUID, request: Request, session: Session) -> AlertRead:
    alert = await repositories.get_alert(session, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    opportunity = await repositories.get_opportunity(session, alert.pair_address)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Associated opportunity not found")
    result = await request.app.state.scanner.notifier.send(
        request.app.state.scanner._opportunity_dict(opportunity),
        payload=alert.payload,
    )
    resent = await repositories.save_alert(
        session,
        pair_address=alert.pair_address,
        success=result.success,
        status_code=result.status_code,
        error=result.error,
        payload=result.payload,
        initial_price_usd=opportunity.price_usd,
    )
    if not result.success:
        raise HTTPException(
            status_code=502,
            detail={"message": "Discord delivery failed", "error": result.error},
        )
    return resent
