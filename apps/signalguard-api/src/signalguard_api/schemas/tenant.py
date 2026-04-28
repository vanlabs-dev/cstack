"""API response models for tenant endpoints. Kept separate from the
domain ``TenantConfig`` so the API can omit secrets (``api_keys``) and
add timing metadata without polluting the schemas package."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantSummary(BaseModel):
    """Per-tenant entry in the GET /tenants list."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    display_name: str
    is_fixture: bool
    added_at: datetime
    last_extract_at: datetime | None = Field(
        default=None,
        description="Most recent raw ingestion across any resource type.",
    )
    last_audit_at: datetime | None = Field(
        default=None,
        description="Most recent non-anomaly finding detected_at.",
    )
    last_anomaly_score_at: datetime | None = Field(
        default=None,
        description="Most recent anomaly_scores.scored_at value.",
    )
    api_key_count: int = 0


class TenantDetail(TenantSummary):
    """Full tenant detail. Drops cert_subject/thumbprint/client_id intentionally
    so the API surface does not become a credential exfiltration vector."""

    pass
