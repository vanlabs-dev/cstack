"""API response models specific to sign-in endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SigninStats(BaseModel):
    """Per-tenant aggregate counters over the sign-in table."""

    tenant_id: str
    total: int
    distinct_users: int
    earliest_at: datetime | None
    latest_at: datetime | None
    success_count: int
    failure_count: int
    top_countries: list[tuple[str, int]] = Field(
        description="Up to 10 countries by sign-in volume.",
    )
    top_apps: list[tuple[str, int]] = Field(
        description="Up to 10 app display names by sign-in volume.",
    )
