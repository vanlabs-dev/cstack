"""Anomaly score model.

Lives in audit-core (not ml-anomaly) so the storage layer can persist scores
without depending on the ML stack. ml-anomaly produces these and treats them
as the public output of scoring.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ShapDirection = Literal["pushes_anomalous", "pushes_normal"]

ModelTier = Literal["per_user", "cold_start_pooled", "rule_only", "unknown"]


class ShapFeatureContribution(BaseModel):
    """One row of SHAP attribution. Direction names spell out the meaning so
    consumers (CLI, future LLM narrator) do not have to interpret signs."""

    model_config = ConfigDict(frozen=True)

    feature_name: str
    feature_value: float
    shap_value: float
    direction: ShapDirection


class AnomalyScore(BaseModel):
    """Per-signin anomaly score with full provenance. Immutable; rerunning
    the scorer with the same model+signin yields the same id key."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    signin_id: str
    user_id: str
    model_name: str
    model_version: str
    raw_score: float
    normalised_score: float
    is_anomaly: bool
    shap_top_features: list[ShapFeatureContribution]
    scored_at: datetime
    model_tier: ModelTier = "unknown"
