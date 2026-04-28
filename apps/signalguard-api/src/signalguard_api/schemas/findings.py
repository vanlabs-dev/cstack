"""API response models specific to findings endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FindingsSummary(BaseModel):
    """Aggregate counts for a tenant's findings table."""

    total: int
    by_category: dict[str, int] = Field(
        description="Counts grouped by category (coverage|rule|exclusion|anomaly)."
    )
    by_severity: dict[str, int] = Field(
        description="Counts grouped by severity (INFO|LOW|MEDIUM|HIGH|CRITICAL)."
    )
    by_rule_id: dict[str, int]
    generated_at: datetime
