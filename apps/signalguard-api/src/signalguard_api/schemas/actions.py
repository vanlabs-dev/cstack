"""Request and response models for action endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from cstack_audit_core import Finding
from pydantic import BaseModel, Field

AuditCategory = Literal["coverage", "rules", "exclusions"]


def _default_audit_categories() -> list[AuditCategory]:
    return ["coverage", "rules", "exclusions"]


class AuditRunRequest(BaseModel):
    """Body of POST /tenants/{id}/audit/run."""

    categories: list[AuditCategory] = Field(
        default_factory=_default_audit_categories,
        description="Subset of audit categories to execute. Empty list rejected.",
    )
    generate_narratives: bool = Field(
        default=True,
        description="When true, run the LLM narrator over written findings.",
    )
    narrative_budget_usd: float | None = Field(
        default=None,
        description="Optional per-run budget cap; falls back to env CSTACK_LLM_BUDGET_USD.",
    )


class NarrativeBatchSummary(BaseModel):
    cache_hits: int
    generated: int
    skipped_budget: int
    errored: int
    dollars_spent: float


class AuditRunResponse(BaseModel):
    findings_written: int
    by_category: dict[str, int]
    duration_seconds: float
    run_id: str
    narrative_summary: NarrativeBatchSummary | None = None


class AuditDryRunResponse(BaseModel):
    findings: list[Finding]
    by_category: dict[str, int]
    run_id: str


class AnomalyScoreRequest(BaseModel):
    since: datetime | None = None
    until: datetime | None = None
    generate_findings: bool = True
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class AnomalyScoreRunResponse(BaseModel):
    signins_scored: int
    anomalies_flagged: int
    findings_written: int
    model_name: str
    model_version: str
    duration_seconds: float
    run_id: str
