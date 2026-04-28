"""Trigger anomaly scoring runs.

Training is intentionally not exposed via HTTP in V1; the MLflow lifecycle
(tracking, registry aliases) is best driven from the CLI where it can be
rolled back if a run goes sideways.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

import duckdb
from cstack_audit_core import write_findings
from cstack_ml_anomaly import findings_from_anomalies, score_batch
from cstack_ml_anomaly.training import pooled_model_name
from cstack_ml_mlops import (
    CHALLENGER_ALIAS,
    CHAMPION_ALIAS,
    configure_tracking,
    get_alias_version,
)
from cstack_storage import get_signins, write_scores
from fastapi import APIRouter, Depends, HTTPException, Request, status

from signalguard_api.auth import require_tenant_access
from signalguard_api.config import Settings, get_settings
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.actions import AnomalyScoreRequest, AnomalyScoreRunResponse

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants/{tenant_id}/anomaly", tags=["anomaly"])


def _ensure_champion(tenant_id: str, tracking_uri: str | None) -> None:
    """Raise 503 if neither @champion nor @challenger exists for the tenant."""
    configure_tracking(uri=tracking_uri)
    name = pooled_model_name(tenant_id)
    for alias in (CHAMPION_ALIAS, CHALLENGER_ALIAS):
        if get_alias_version(name, alias) is not None:
            return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"no @{CHAMPION_ALIAS} or @{CHALLENGER_ALIAS} version of {name} registered; "
            f"run `cstack anomaly train --tenant {tenant_id}` first"
        ),
    )


@router.post(
    "/score",
    response_model=AnomalyScoreRunResponse,
    summary="Score recent sign-ins against the registered model",
    description=(
        "Loads sign-ins in the requested window, scores them with the current "
        "@champion (or @challenger fallback), persists scores, and optionally "
        "writes findings for anomalies above threshold."
    ),
    responses={
        503: {
            "description": "No @champion or @challenger model registered for tenant.",
        }
    },
)
async def score(
    body: AnomalyScoreRequest,
    request: Request,
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
) -> AnomalyScoreRunResponse:
    _ = request
    _ensure_champion(tenant_id, settings.mlflow_tracking_uri)
    run_id = str(uuid.uuid4())
    started = time.perf_counter()

    def _execute() -> AnomalyScoreRunResponse:
        signins = get_signins(conn, tenant_id, since=body.since, until=body.until)
        if not signins:
            duration = time.perf_counter() - started
            return AnomalyScoreRunResponse(
                signins_scored=0,
                anomalies_flagged=0,
                findings_written=0,
                model_name=pooled_model_name(tenant_id),
                model_version="",
                duration_seconds=duration,
                run_id=run_id,
            )
        scores = score_batch(signins, tenant_id, conn, tracking_uri=settings.mlflow_tracking_uri)
        write_scores(conn, scores)
        n_anom = sum(1 for s in scores if s.is_anomaly)
        findings_written = 0
        if body.generate_findings and scores:
            findings = findings_from_anomalies(scores, tenant_id, threshold=body.threshold)
            findings_written = write_findings(conn, findings)
        duration = time.perf_counter() - started
        version = scores[0].model_version if scores else ""
        LOG.info(
            "anomaly score run completed",
            extra={
                "tenant_id": tenant_id,
                "run_id": run_id,
                "signins_scored": len(scores),
                "anomalies_flagged": n_anom,
                "findings_written": findings_written,
                "duration_seconds": round(duration, 3),
            },
        )
        return AnomalyScoreRunResponse(
            signins_scored=len(scores),
            anomalies_flagged=n_anom,
            findings_written=findings_written,
            model_name=scores[0].model_name if scores else pooled_model_name(tenant_id),
            model_version=version,
            duration_seconds=duration,
            run_id=run_id,
        )

    return await asyncio.to_thread(_execute)
