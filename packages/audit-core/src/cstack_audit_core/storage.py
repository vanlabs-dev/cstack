import json
from typing import Any

import duckdb

from cstack_audit_core.finding import AffectedObject, Finding
from cstack_audit_core.severity import Severity


def write_findings(conn: duckdb.DuckDBPyConnection, findings: list[Finding]) -> int:
    """Insert findings, skipping any whose id already exists.

    Findings are immutable. Repeating a write of the same finding is a
    no-op so first_seen_at survives. Returns the number of newly-inserted
    rows.
    """
    if not findings:
        return 0
    inserted = 0
    for finding in findings:
        existing = conn.execute("SELECT 1 FROM findings WHERE id = ?", [finding.id]).fetchone()
        if existing is not None:
            continue
        conn.execute(
            """
            INSERT INTO findings (
                id, tenant_id, rule_id, category, severity, title, summary,
                affected_objects, evidence, remediation_hint, "references",
                detected_at, first_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                finding.id,
                finding.tenant_id,
                finding.rule_id,
                finding.category,
                finding.severity.value,
                finding.title,
                finding.summary,
                json.dumps([o.model_dump() for o in finding.affected_objects]),
                json.dumps(finding.evidence, default=str),
                finding.remediation_hint,
                json.dumps(finding.references),
                finding.detected_at,
                finding.first_seen_at,
            ],
        )
        inserted += 1
    return inserted


def latest_findings(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    category: str | None = None,
    min_severity: Severity | None = None,
    rule_id: str | None = None,
) -> list[Finding]:
    """Read findings for a tenant with optional filters."""
    sql_parts: list[str] = [
        """
        SELECT id, tenant_id, rule_id, category, severity, title, summary,
               affected_objects, evidence, remediation_hint, "references",
               detected_at, first_seen_at
        FROM findings WHERE tenant_id = ?
        """
    ]
    params: list[Any] = [tenant_id]
    if category is not None:
        sql_parts.append(" AND category = ?")
        params.append(category)
    if rule_id is not None:
        sql_parts.append(" AND rule_id = ?")
        params.append(rule_id)
    if min_severity is not None:
        allowed = [s.value for s in Severity if s >= min_severity]
        placeholders = ", ".join(["?"] * len(allowed))
        sql_parts.append(f" AND severity IN ({placeholders})")
        params.extend(allowed)
    sql_parts.append(" ORDER BY severity DESC, first_seen_at DESC")
    rows = conn.execute("".join(sql_parts), params).fetchall()
    return [_row_to_finding(row) for row in rows]


def findings_by_rule(
    conn: duckdb.DuckDBPyConnection, tenant_id: str, rule_id: str
) -> list[Finding]:
    return latest_findings(conn, tenant_id, rule_id=rule_id)


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
