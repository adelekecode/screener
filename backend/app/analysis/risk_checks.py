from typing import Any


def build_risk_flags(checks: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    labels = {
        "mint_authority_revoked": "Mint authority status unavailable",
        "freeze_authority_revoked": "Freeze authority status unavailable",
        "top_10_holder_percentage": "Holder concentration unavailable",
        "creator_percentage": "Creator allocation unavailable",
        "unique_buyers_10m": "Unique buyer count unavailable",
    }
    for key, label in labels.items():
        if checks.get(key) is None:
            flags.append(label)
    if checks.get("mint_authority_revoked") is False:
        flags.append("Mint authority is active")
    if checks.get("freeze_authority_revoked") is False:
        flags.append("Freeze authority is active")
    return flags

