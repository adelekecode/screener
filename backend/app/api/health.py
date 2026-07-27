from fastapi import APIRouter, Request
from sqlalchemy import text

from app.database.session import SessionLocal
from app.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    database_status = "ok"
    redis_status = "ok"
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    try:
        await request.app.state.redis.ping()
    except Exception:
        redis_status = "unavailable"
    scanner = request.app.state.scanner
    try:
        scanner_status = "paused" if await scanner.is_paused() else "running"
    except Exception:
        scanner_status = "unknown"
    status = "ok" if database_status == redis_status == "ok" else "degraded"
    return HealthResponse(
        status=status,
        database=database_status,
        redis=redis_status,
        scanner=scanner_status,
    )

