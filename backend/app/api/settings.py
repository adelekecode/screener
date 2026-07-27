from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Criteria, get_settings
from app.database import repositories
from app.database.session import get_session
from app.schemas import SettingsPatch, SettingsRead

router = APIRouter(prefix="/api/settings", tags=["settings"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def _settings_response(request: Request, session: AsyncSession) -> SettingsRead:
    app_settings = get_settings()
    criteria_overrides = await repositories.get_setting(session, "criteria", {})
    interval = await repositories.get_setting(
        session, "scan_interval_minutes", app_settings.scan_interval_minutes
    )
    webhook = await repositories.get_setting(
        session, "discord_webhook_url", app_settings.discord_webhook_url
    )
    return SettingsRead(
        criteria=app_settings.load_criteria(criteria_overrides).model_dump(),
        scan_interval_minutes=interval,
        scanner_paused=await request.app.state.scanner.is_paused(),
        discord_configured=bool(webhook),
    )


@router.get("", response_model=SettingsRead)
async def read_settings(request: Request, session: Session) -> SettingsRead:
    return await _settings_response(request, session)


@router.patch("", response_model=SettingsRead)
async def patch_settings(
    changes: SettingsPatch, request: Request, session: Session
) -> SettingsRead:
    if changes.criteria is not None:
        current = await repositories.get_setting(session, "criteria", {})
        validated = Criteria.model_validate(
            {**get_settings().load_criteria(current).model_dump(), **changes.criteria}
        )
        await repositories.set_setting(session, "criteria", validated.model_dump())

    if changes.scan_interval_minutes is not None:
        await repositories.set_setting(
            session, "scan_interval_minutes", changes.scan_interval_minutes
        )
        request.app.state.scheduler.reschedule_job(
            "memecoin-scan",
            trigger="interval",
            minutes=changes.scan_interval_minutes,
        )
        request.app.state.scheduler.reschedule_job(
            "token-tracker",
            trigger="interval",
            minutes=changes.scan_interval_minutes,
        )

    if changes.discord_webhook_url is not None:
        webhook = changes.discord_webhook_url.strip() or None
        await repositories.set_setting(session, "discord_webhook_url", webhook)
        request.app.state.scanner.notifier.webhook_url = webhook

    return await _settings_response(request, session)
