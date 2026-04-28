"""API response models specific to anomaly endpoints."""

from __future__ import annotations

from cstack_audit_core import AnomalyScore, Finding
from cstack_schemas import SignIn
from pydantic import BaseModel


class AnomalyScoreDetail(BaseModel):
    """Per-signin anomaly bundle: score, raw signin row, and linked finding."""

    score: AnomalyScore
    signin: SignIn
    finding: Finding | None
