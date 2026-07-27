import os
from typing import Any

import httpx

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


class APIError(RuntimeError):
    pass


def request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = httpx.request(
            method, f"{BASE_URL}{path}", timeout=30, follow_redirects=True, **kwargs
        )
        response.raise_for_status()
        return response.json() if response.content else None
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        raise APIError(str(detail)) from exc
    except httpx.HTTPError as exc:
        raise APIError(f"Backend unavailable at {BASE_URL}: {exc}") from exc


def get(path: str, **params: Any) -> Any:
    return request("GET", path, params={k: v for k, v in params.items() if v is not None})


def post(path: str, payload: dict[str, Any] | None = None) -> Any:
    return request("POST", path, json=payload)


def patch(path: str, payload: dict[str, Any]) -> Any:
    return request("PATCH", path, json=payload)

