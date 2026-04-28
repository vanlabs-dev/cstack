"""Model registry endpoints. Project MLflow registry state into the API.

Routers do not call ``MlflowClient`` directly; the helpers in
``cstack-ml-mlops`` are the only allowed surface area so MLflow swaps
(e.g. moving from file backend to SQL) stay localised.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from cstack_ml_anomaly.training import pooled_model_name
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    configure_tracking,
    get_alias_version,
    get_run_metrics,
    list_model_versions,
    search_registered_models,
)
from fastapi import APIRouter, Depends

from signalguard_api.auth import require_tenant_access
from signalguard_api.config import Settings, get_settings
from signalguard_api.schemas.models import ModelSummary, ModelVersionEntry

router = APIRouter(prefix="/tenants/{tenant_id}/models", tags=["models"])


def _from_ms(value: int | None) -> datetime | None:
    """MLflow returns timestamps as milliseconds-since-epoch."""
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000.0, tz=UTC)


def _project_version(model_name: str, mv: object) -> ModelVersionEntry:
    return ModelVersionEntry(
        name=model_name,
        version=str(getattr(mv, "version", "")),
        run_id=getattr(mv, "run_id", None) or None,
        aliases=list(getattr(mv, "aliases", []) or []),
        creation_timestamp=_from_ms(getattr(mv, "creation_timestamp", None)),
        last_updated_timestamp=_from_ms(getattr(mv, "last_updated_timestamp", None)),
        metrics=get_run_metrics(getattr(mv, "run_id", "") or ""),
    )


def _summary_for_tenant(tenant_id: str) -> list[ModelSummary]:
    name = pooled_model_name(tenant_id)
    matches = search_registered_models(name_prefix=name)
    if not matches:
        return []
    summaries: list[ModelSummary] = []
    for rm in matches:
        rm_name = getattr(rm, "name", name)
        champion = get_alias_version(rm_name, CHAMPION_ALIAS)
        challenger = get_alias_version(rm_name, CHALLENGER_ALIAS)
        latest_versions = list_model_versions(rm_name)
        last_trained_at = (
            _from_ms(getattr(latest_versions[0], "creation_timestamp", None))
            if latest_versions
            else None
        )
        latest_run_id = getattr(latest_versions[0], "run_id", None) if latest_versions else None
        metrics = get_run_metrics(latest_run_id) if latest_run_id else {}
        summaries.append(
            ModelSummary(
                name=rm_name,
                current_champion_version=str(champion.version) if champion is not None else None,
                current_challenger_version=str(challenger.version)
                if challenger is not None
                else None,
                last_trained_at=last_trained_at,
                training_metrics=metrics,
            )
        )
    return summaries


@router.get(
    "",
    response_model=list[ModelSummary],
    summary="List registered models for a tenant",
    description=(
        "Reads the MLflow registry for models matching the tenant's pooled-model "
        "naming convention. Returns an empty list when no models are registered."
    ),
)
async def list_models(
    tenant_id: str = Depends(require_tenant_access),
    settings: Settings = Depends(get_settings),
) -> list[ModelSummary]:
    def _query() -> list[ModelSummary]:
        configure_tracking(uri=settings.mlflow_tracking_uri)
        return _summary_for_tenant(tenant_id)

    return await asyncio.to_thread(_query)


@router.get(
    "/{model_name}/versions",
    response_model=list[ModelVersionEntry],
    summary="List versions of a registered model",
)
async def list_versions(
    model_name: str,
    tenant_id: str = Depends(require_tenant_access),
    settings: Settings = Depends(get_settings),
) -> list[ModelVersionEntry]:
    _ = tenant_id

    def _query() -> list[ModelVersionEntry]:
        configure_tracking(uri=settings.mlflow_tracking_uri)
        return [_project_version(model_name, mv) for mv in list_model_versions(model_name)]

    return await asyncio.to_thread(_query)
