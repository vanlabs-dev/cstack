"""``/whoami`` returns the resolved caller. Useful for verifying a freshly
issued API key without invoking a domain-scoped route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from signalguard_api.auth import ApiCaller, require_api_key

router = APIRouter(tags=["health"])


@router.get(
    "/whoami",
    summary="Identify the caller",
    description="Returns the resolved API caller (dev or tenant-scoped).",
)
async def whoami(caller: ApiCaller = Depends(require_api_key)) -> ApiCaller:
    return caller
