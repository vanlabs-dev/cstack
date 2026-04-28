"""Audit and anomaly findings endpoints."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal

import duckdb
from cstack_audit_core import AffectedObject, Finding, Severity
from fastapi import APIRouter, Depends, HTTPException, Query, status

from signalguard_api.auth import require_tenant_access
from signalguard_api.dependencies import get_db_connection
from signalguard_api.schemas.findings import FindingsSummary
from signalguard_api.schemas.pagination import Paginated

router = APIRouter(prefix="/tenants/{tenant_id}/findings", tags=["findings"])

CategoryLiteral = Literal["coverage", "rule", "exclusion", "anomaly"]


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
    category: list[str] | None,
    min_severity: Severity | None,
    rule_id: str | None,
    since: datetime | None,
) -> tuple[str, list[Any]]:
    """Compose the WHERE clause and parameter list for findings queries.

    Returned SQL begins with ``WHERE`` and contains no leading whitespace so
    callers can splice it directly after the SELECT clause.
    """
    parts: list[str] = ["WHERE tenant_id = ?"]
    params: list[Any] = [tenant_id]
    if category:
        placeholders = ", ".join(["?"] * len(category))
        parts.append(f"AND category IN ({placeholders})")
        params.extend(category)
    if rule_id is not None:
        parts.append("AND rule_id = ?")
        params.append(rule_id)
    if min_severity is not None:
        allowed = [s.value for s in Severity if s >= min_severity]
        ph = ", ".join(["?"] * len(allowed))
        parts.append(f"AND severity IN ({ph})")
        params.extend(allowed)
    if since is not None:
        parts.append("AND first_seen_at >= ?")
        params.append(since)
    return " ".join(parts), params


@router.get(
    "",
    response_model=Paginated[Finding],
    summary="List findings for a tenant",
    description=(
        "Filterable, paginated read of the findings table. Severity filter "
        "is inclusive of the requested floor and above."
    ),
)
async def list_findings(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
    category: list[CategoryLiteral] | None = Query(default=None),
    min_severity: Severity | None = Query(default=None),
    rule_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Paginated[Finding]:
    cat_strings = [str(c) for c in category] if category else None

    def _query() -> Paginated[Finding]:
        where, params = _build_filters(tenant_id, cat_strings, min_severity, rule_id, since)
        total_row = conn.execute(f"SELECT COUNT(*) FROM findings {where}", params).fetchone()
        total = int(total_row[0]) if total_row else 0
        rows = conn.execute(
            f"""
            SELECT id, tenant_id, rule_id, category, severity, title, summary,
                   affected_objects, evidence, remediation_hint, "references",
                   detected_at, first_seen_at
            FROM findings
            {where}
            ORDER BY severity DESC, first_seen_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        items = [_row_to_finding(row) for row in rows]
        return Paginated[Finding](
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )

    return await asyncio.to_thread(_query)


@router.get(
    "/summary",
    response_model=FindingsSummary,
    summary="Per-tenant finding aggregates",
)
async def findings_summary(
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> FindingsSummary:
    def _query() -> FindingsSummary:
        rows = conn.execute(
            "SELECT category, severity, rule_id FROM findings WHERE tenant_id = ?",
            [tenant_id],
        ).fetchall()
        categories: Counter[str] = Counter()
        severities: Counter[str] = Counter()
        rule_ids: Counter[str] = Counter()
        for cat, sev, rid in rows:
            categories[cat] += 1
            severities[sev] += 1
            rule_ids[rid] += 1
        return FindingsSummary(
            total=len(rows),
            by_category=dict(categories),
            by_severity=dict(severities),
            by_rule_id=dict(rule_ids),
            generated_at=datetime.now(UTC),
        )

    return await asyncio.to_thread(_query)


@router.get(
    "/{finding_id}",
    response_model=Finding,
    summary="Read a single finding by id",
)
async def get_finding(
    finding_id: str,
    tenant_id: str = Depends(require_tenant_access),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> Finding:
    def _query() -> Finding:
        row = conn.execute(
            """
            SELECT id, tenant_id, rule_id, category, severity, title, summary,
                   affected_objects, evidence, remediation_hint, "references",
                   detected_at, first_seen_at
            FROM findings WHERE tenant_id = ? AND id = ?
            """,
            [tenant_id, finding_id],
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"finding '{finding_id}' not found for tenant '{tenant_id}'",
            )
        return _row_to_finding(row)

    return await asyncio.to_thread(_query)
