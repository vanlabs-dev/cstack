"""Anomaly score read endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

import duckdb
from cstack_audit_core import (
    AffectedObject,
    AnomalyScore,
    Finding,
    Severity,
    ShapFeatureContribution,
)
from cstack_schemas import SignIn
from fastapi import APIRouter, Depends, HTTPException, Query, status

from signalguard_api.auth import require_tenant_access
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.anomaly import AnomalyScoreDetail
from signalguard_api.schemas.pagination import Paginated

router = APIRouter(prefix="/tenants/{tenant_id}/anomaly-scores", tags=["anomaly"])

_SCORE_COLUMNS = (
    "tenant_id, signin_id, user_id, model_name, model_version, raw_score, "
    "normalised_score, is_anomaly, shap_top_features, scored_at"
)


def _row_to_score(row: tuple[Any, ...]) -> AnomalyScore:
    return AnomalyScore(
        tenant_id=row[0],
        signin_id=row[1],
        user_id=row[2],
        model_name=row[3],
        model_version=row[4],
        raw_score=row[5],
        normalised_score=row[6],
        is_anomaly=row[7],
        shap_top_features=[ShapFeatureContribution.model_validate(f) for f in json.loads(row[8])],
        scored_at=row[9],
    )


def _row_to_finding(row: tuple[Any, ...]) -> Finding:
    return Finding(
        id=row[0],
        tenant_id=row[1],
        rule_id=row[2],
        category=row[3],
        severity=Severity(row[4]),
        title=row[5],
        summary=row[6],
        affected_objects=[AffectedObject.model_validate(o) for o in json.loads(row[7])],
        evidence=json.loads(row[8]),
        remediation_hint=row[9],
        references=json.loads(row[10]),
        detected_at=row[11],
        first_seen_at=row[12],
    )


def _build_filters(
    tenant_id: str,
    user_id: str | None,
    min_score: float,
    is_anomaly: bool | None,
    since: datetime | None,
) -> tuple[str, list[Any]]:
    parts = ["WHERE tenant_id = ?"]
    params: list[Any] = [tenant_id]
    if user_id is not None:
        parts.append("AND user_id = ?")
        params.append(user_id)
    if min_score > 0.0:
        parts.append("AND normalised_score >= ?")
        params.append(min_score)
    if is_anomaly is not None:
        parts.append("AND is_anomaly = ?")
        params.append(is_anomaly)
    if since is not None:
        parts.append("AND scored_at >= ?")
        params.append(since)
    return " ".join(parts), params


@router.get(
    "",
    response_model=Paginated[AnomalyScore],
    summary="List anomaly scores for a tenant",
)
async def list_scores(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
    user_id: str | None = Query(default=None),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    is_anomaly: bool | None = Query(default=None),
    since: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Paginated[AnomalyScore]:
    def _query() -> Paginated[AnomalyScore]:
        where, params = _build_filters(tenant_id, user_id, min_score, is_anomaly, since)
        total_row = conn.execute(f"SELECT COUNT(*) FROM anomaly_scores {where}", params).fetchone()
        total = int(total_row[0]) if total_row else 0
        rows = conn.execute(
            f"""
            SELECT {_SCORE_COLUMNS}
            FROM anomaly_scores
            {where}
            ORDER BY normalised_score DESC, scored_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        items = [_row_to_score(row) for row in rows]
        return Paginated[AnomalyScore](
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    return await asyncio.to_thread(_query)


@router.get(
    "/feed",
    response_model=list[AnomalyScore],
    summary="Latest anomalies above threshold",
    description="Convenience read for dashboard timelines.",
)
async def feed(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
    n: int = Query(default=50, ge=1, le=200),
    min_score: float = Query(default=0.7, ge=0.0, le=1.0),
) -> list[AnomalyScore]:
    def _query() -> list[AnomalyScore]:
        rows = conn.execute(
            f"""
            SELECT {_SCORE_COLUMNS}
            FROM anomaly_scores
            WHERE tenant_id = ? AND is_anomaly = TRUE AND normalised_score >= ?
            ORDER BY normalised_score DESC, scored_at DESC
            LIMIT ?
            """,
            [tenant_id, min_score, n],
        ).fetchall()
        return [_row_to_score(row) for row in rows]

    return await asyncio.to_thread(_query)


@router.get(
    "/{signin_id}",
    response_model=AnomalyScoreDetail,
    summary="Anomaly score with linked sign-in and finding",
)
async def get_detail(
    signin_id: str,
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> AnomalyScoreDetail:
    def _query() -> AnomalyScoreDetail:
        score_row = conn.execute(
            f"""
            SELECT {_SCORE_COLUMNS}
            FROM anomaly_scores
            WHERE tenant_id = ? AND signin_id = ?
            ORDER BY scored_at DESC
            LIMIT 1
            """,
            [tenant_id, signin_id],
        ).fetchone()
        if score_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no anomaly score for signin '{signin_id}' under tenant '{tenant_id}'",
            )
        score = _row_to_score(score_row)

        signin_row = conn.execute(
            "SELECT raw_payload FROM signins WHERE tenant_id = ? AND id = ?",
            [tenant_id, signin_id],
        ).fetchone()
        if signin_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"signin '{signin_id}' missing under tenant '{tenant_id}'",
            )
        signin = SignIn.model_validate(json.loads(signin_row[0]))

        finding_id = Finding.compute_id(tenant_id, "anomaly.signin", [signin_id])
        finding_row = conn.execute(
            """
            SELECT id, tenant_id, rule_id, category, severity, title, summary,
                   affected_objects, evidence, remediation_hint, "references",
                   detected_at, first_seen_at
            FROM findings WHERE tenant_id = ? AND id = ?
            """,
            [tenant_id, finding_id],
        ).fetchone()
        finding = _row_to_finding(finding_row) if finding_row is not None else None
        return AnomalyScoreDetail(score=score, signin=signin, finding=finding)

    return await asyncio.to_thread(_query)
