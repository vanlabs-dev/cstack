"""Sign-in stats and per-user history endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import duckdb
from cstack_schemas import SignIn
from fastapi import APIRouter, Depends, Query

from signalguard_api.auth import require_tenant_access
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.pagination import Paginated
from signalguard_api.schemas.signins import SigninStats

stats_router = APIRouter(prefix="/tenants/{tenant_id}/signins", tags=["signins"])
user_router = APIRouter(prefix="/tenants/{tenant_id}/users", tags=["signins"])


def _top_n(conn: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> list[tuple[str, int]]:
    rows = conn.execute(sql, params).fetchall()
    return [(str(r[0]) if r[0] is not None else "(unknown)", int(r[1])) for r in rows]


@stats_router.get(
    "/stats",
    response_model=SigninStats,
    summary="Tenant sign-in aggregates",
)
async def get_stats(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> SigninStats:
    def _query() -> SigninStats:
        agg = conn.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT user_id),
                   MIN(created_date_time), MAX(created_date_time),
                   COALESCE(SUM(CASE
                       WHEN error_code = 0 OR error_code IS NULL THEN 1 ELSE 0
                   END), 0),
                   COALESCE(SUM(CASE
                       WHEN error_code IS NOT NULL AND error_code != 0 THEN 1 ELSE 0
                   END), 0)
            FROM signins WHERE tenant_id = ?
            """,
            [tenant_id],
        ).fetchone()
        if agg is None:
            return SigninStats(
                tenant_id=tenant_id,
                total=0,
                distinct_users=0,
                earliest_at=None,
                latest_at=None,
                success_count=0,
                failure_count=0,
                top_countries=[],
                top_apps=[],
            )
        countries = _top_n(
            conn,
            """
            SELECT country_or_region, COUNT(*) FROM signins
            WHERE tenant_id = ? AND country_or_region IS NOT NULL
            GROUP BY country_or_region ORDER BY COUNT(*) DESC LIMIT 10
            """,
            [tenant_id],
        )
        apps = _top_n(
            conn,
            """
            SELECT app_display_name, COUNT(*) FROM signins
            WHERE tenant_id = ? AND app_display_name IS NOT NULL
            GROUP BY app_display_name ORDER BY COUNT(*) DESC LIMIT 10
            """,
            [tenant_id],
        )
        return SigninStats(
            tenant_id=tenant_id,
            total=int(agg[0]),
            distinct_users=int(agg[1]),
            earliest_at=agg[2],
            latest_at=agg[3],
            success_count=int(agg[4]),
            failure_count=int(agg[5]),
            top_countries=countries,
            top_apps=apps,
        )

    return await asyncio.to_thread(_query)


@user_router.get(
    "/{user_id}/signins",
    response_model=Paginated[SignIn],
    summary="Per-user sign-in history",
)
async def get_user_signins(
    user_id: str,
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Paginated[SignIn]:
    def _query() -> Paginated[SignIn]:
        total_row = conn.execute(
            "SELECT COUNT(*) FROM signins WHERE tenant_id = ? AND user_id = ?",
            [tenant_id, user_id],
        ).fetchone()
        total = int(total_row[0]) if total_row else 0
        rows = conn.execute(
            """
            SELECT raw_payload FROM signins
            WHERE tenant_id = ? AND user_id = ?
            ORDER BY created_date_time DESC
            LIMIT ? OFFSET ?
            """,
            [tenant_id, user_id, limit, offset],
        ).fetchall()
        items = [SignIn.model_validate(json.loads(r[0])) for r in rows]
        return Paginated[SignIn](
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    return await asyncio.to_thread(_query)
