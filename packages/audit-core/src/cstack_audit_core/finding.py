import hashlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from cstack_audit_core.severity import Severity

AffectedObjectType = Literal["policy", "user", "group", "role", "location", "app", "tenant"]
FindingCategory = Literal["coverage", "rule", "exclusion"]


class AffectedObject(BaseModel):
    """A target the finding refers to. Carries enough identification for the
    LLM narrator and the UI to render the object without re-querying Graph.
    """

    model_config = ConfigDict(frozen=True)

    type: AffectedObjectType
    id: str
    display_name: str


class Finding(BaseModel):
    """An immutable audit finding. Identity is computed from inputs so the
    same finding produced twice in a row writes one row.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    tenant_id: str
    rule_id: str
    category: FindingCategory
    severity: Severity
    title: str
    summary: str
    affected_objects: list[AffectedObject]
    evidence: dict[str, Any]
    remediation_hint: str
    references: list[str]
    detected_at: datetime
    first_seen_at: datetime

    @classmethod
    def compute_id(
        cls,
        tenant_id: str,
        rule_id: str,
        affected_object_ids: list[str],
    ) -> str:
        """Deterministic SHA-256-derived id, sorted-input-stable.

        Truncated to 32 hex chars (128 bits): collision-resistant for any
        realistic finding volume and short enough to render in tables.
        """
        sorted_ids = sorted(affected_object_ids)
        payload = f"{tenant_id}|{rule_id}|{','.join(sorted_ids)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
