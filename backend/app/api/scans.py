from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import repositories
from app.database.session import get_session
from app.schemas import ScanRead, StatsRead

router = APIRouter(prefix="/api", tags=["scanner"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/scans", response_model=list[ScanRead])
async def scans(
    session: Session, limit: int = Query(default=100, ge=1, le=500)
) -> list[ScanRead]:
    return await repositories.list_scans(session, limit=limit)


@router.post("/scans/run", status_code=status.HTTP_202_ACCEPTED)
async def run_scan(request: Request) -> dict[str, str]:
    scanner = request.app.state.scanner
    if await scanner.is_paused():
        raise HTTPException(status_code=409, detail="Scanner is paused")
    if not scanner.start_scan():
        raise HTTPException(status_code=409, detail="A scan is already running")
    return {"status": "accepted"}


@router.post("/scanner/pause")
async def pause_scanner(request: Request) -> dict[str, str]:
    await request.app.state.scanner.pause()
    return {"status": "paused"}


@router.post("/scanner/resume")
async def resume_scanner(request: Request) -> dict[str, str]:
    await request.app.state.scanner.resume()
    return {"status": "running"}


@router.get("/stats", response_model=StatsRead)
async def stats(request: Request, session: Session) -> StatsRead:
    values = await repositories.get_stats(session)
    scheduler = request.app.state.scheduler
    job = scheduler.get_job("memecoin-scan")
    return StatsRead(
        **values,
        next_scan_at=job.next_run_time if job else None,
        scanner_paused=await request.app.state.scanner.is_paused(),
    )

