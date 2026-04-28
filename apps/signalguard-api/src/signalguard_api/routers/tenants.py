"""Tenant inventory endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import duckdb
from cstack_storage import get_tenant_db, list_tenants_db
from fastapi import APIRouter, Depends, HTTPException, status

from signalguard_api.auth import require_dev, require_tenant_access
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.tenant import TenantDetail, TenantSummary

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _last_extract_at(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> datetime | None:
    row = conn.execute(
        "SELECT MAX(ingested_at) FROM raw_ingestions WHERE tenant_id = ?",
        [tenant_id],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _last_audit_at(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> datetime | None:
    row = conn.execute(
        """
        SELECT MAX(detected_at) FROM findings
        WHERE tenant_id = ? AND category != 'anomaly'
        """,
        [tenant_id],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _last_anomaly_at(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> datetime | None:
    row = conn.execute(
        "SELECT MAX(scored_at) FROM anomaly_scores WHERE tenant_id = ?",
        [tenant_id],
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _api_key_count(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> int:
    """Tenants.json holds the keys; API never reads from the DB for this. Returns
    0 here as a sentinel because the DB-listed tenants do not carry keys."""
    _ = (conn, tenant_id)
    return 0


def _build_summary(conn: duckdb.DuckDBPyConnection, tenant: Any) -> TenantSummary:
    return TenantSummary(
        tenant_id=tenant.tenant_id,
        display_name=tenant.display_name,
        is_fixture=tenant.is_fixture,
        added_at=tenant.added_at,
        last_extract_at=_last_extract_at(conn, tenant.tenant_id),
        last_audit_at=_last_audit_at(conn, tenant.tenant_id),
        last_anomaly_score_at=_last_anomaly_at(conn, tenant.tenant_id),
        api_key_count=_api_key_count(conn, tenant.tenant_id),
    )


@router.get(
    "",
    response_model=list[TenantSummary],
    summary="List registered tenants",
    description="Dev-only endpoint that returns every tenant the storage layer knows about.",
    dependencies=[Depends(require_dev)],
)
async def list_tenants(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> list[TenantSummary]:
    def _query() -> list[TenantSummary]:
        return [_build_summary(conn, t) for t in list_tenants_db(conn)]

    return await asyncio.to_thread(_query)


@router.get(
    "/{tenant_id}",
    response_model=TenantDetail,
    summary="Get tenant detail",
    description="Per-tenant detail. Tenant-scoped keys can only read their own row.",
)
async def get_tenant_detail(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> TenantDetail:
    def _query() -> TenantDetail:
        tenant = get_tenant_db(conn, tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"tenant '{tenant_id}' not registered",
            )
        summary = _build_summary(conn, tenant)
        return TenantDetail(**summary.model_dump())

    return await asyncio.to_thread(_query)
