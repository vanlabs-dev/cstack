"""API response models for the model registry endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ModelVersionEntry(BaseModel):
    """One ModelVersion projected to fields the dashboard needs."""

    name: str
    version: str
    run_id: str | None
    aliases: list[str]
    creation_timestamp: datetime | None
    last_updated_timestamp: datetime | None
    metrics: dict[str, float]


class ModelSummary(BaseModel):
    """Top-level entry in GET /tenants/{id}/models."""

    name: str
    current_champion_version: str | None
    current_challenger_version: str | None
    last_trained_at: datetime | None
    training_metrics: dict[str, float]
