"""Tests for the model registry endpoints."""

from __future__ import annotations

import time

import mlflow
import pytest
from cstack_ml_anomaly.training import pooled_model_name
from cstack_ml_mlops import CHALLENGER_ALIAS, CHAMPION_ALIAS, configure_tracking, set_alias
from httpx import AsyncClient
from signalguard_api.config import Settings

from .conftest import DEV_KEY, TENANT_A


@pytest.mark.asyncio
async def test_models_empty_for_unregistered_tenant(client: AsyncClient) -> None:
    response = await client.get(f"/tenants/{TENANT_A}/models", headers={"X-API-Key": DEV_KEY})
    assert response.status_code == 200
    assert response.json() == []


def _seed_registered_model(settings: Settings) -> str:
    configure_tracking(uri=settings.mlflow_tracking_uri)
    name = pooled_model_name(TENANT_A)
    client = mlflow.tracking.MlflowClient()
    client.create_registered_model(name)
    with mlflow.start_run() as run:
        mlflow.log_metric("n_signins_used", 123.0)
        mlflow.log_metric("training_duration_seconds", 1.5)
    mv = client.create_model_version(
        name=name, source=run.info.artifact_uri, run_id=run.info.run_id
    )
    set_alias(name, mv.version, CHALLENGER_ALIAS)
    set_alias(name, mv.version, CHAMPION_ALIAS)
    # MLflow's file backend writes timestamps from epoch ms; smoke a tiny sleep
    # so creation timestamps differ in tests that register a second version.
    time.sleep(0.005)
    return name


@pytest.mark.asyncio
async def test_models_returns_summary_for_registered(
    client: AsyncClient, settings: Settings
) -> None:
    model_name = _seed_registered_model(settings)
    response = await client.get(f"/tenants/{TENANT_A}/models", headers={"X-API-Key": DEV_KEY})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["name"] == model_name
    assert entry["current_champion_version"] == "1"
    assert entry["current_challenger_version"] == "1"
    assert entry["last_trained_at"] is not None
    assert entry["training_metrics"]["n_signins_used"] == 123.0


@pytest.mark.asyncio
async def test_model_versions_endpoint(client: AsyncClient, settings: Settings) -> None:
    model_name = _seed_registered_model(settings)
    response = await client.get(
        f"/tenants/{TENANT_A}/models/{model_name}/versions",
        headers={"X-API-Key": DEV_KEY},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["version"] == "1"
    assert CHAMPION_ALIAS in entry["aliases"]
    assert CHALLENGER_ALIAS in entry["aliases"]
