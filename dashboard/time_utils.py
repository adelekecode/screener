from datetime import UTC, datetime
from typing import Any


def _as_utc(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def humanize_timestamp(value: Any, *, now: datetime | None = None) -> str:
    parsed = _as_utc(value)
    if parsed is None:
        return "Unknown"

    current = (now or datetime.now(UTC)).astimezone(UTC)
    seconds = max(0, int((current - parsed).total_seconds()))
    if seconds < 60:
        return "Just now"
    if seconds < 3_600:
        minutes = seconds // 60
        return f"{minutes} min ago"
    if seconds < 86_400:
        hours = seconds // 3_600
        return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"
    if seconds < 604_800:
        days = seconds // 86_400
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    return parsed.strftime("%d %b %Y")


def friendly_utc_timestamp(value: Any) -> str:
    parsed = _as_utc(value)
    return parsed.strftime("%d %b %Y at %H:%M UTC") if parsed else "Unknown"

