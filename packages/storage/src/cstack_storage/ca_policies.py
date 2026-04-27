import json
from datetime import UTC, datetime

import duckdb
from cstack_schemas import ConditionalAccessPolicy


def upsert_ca_policies(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    policies: list[ConditionalAccessPolicy],
) -> int:
    """Insert or replace conditional access policies. Returns rows written."""
    if not policies:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            tenant_id,
            policy.id,
            policy.display_name,
            policy.state,
            policy.created_date_time,
            policy.modified_date_time,
            policy.conditions.model_dump_json(by_alias=True, exclude_none=True)
            if policy.conditions is not None
            else None,
            policy.grant_controls.model_dump_json(by_alias=True, exclude_none=True)
            if policy.grant_controls is not None
            else None,
            policy.session_controls.model_dump_json(by_alias=True, exclude_none=True)
            if policy.session_controls is not None
            else None,
            now,
        )
        for policy in policies
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO ca_policies
            (tenant_id, id, display_name, state, created_at, modified_at,
             conditions, grant_controls, session_controls, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def get_policies(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> list[ConditionalAccessPolicy]:
    """Read parsed CA policies for a tenant."""
    rows = conn.execute(
        """
        SELECT id, display_name, state, created_at, modified_at,
               conditions, grant_controls, session_controls
        FROM ca_policies WHERE tenant_id = ?
        ORDER BY display_name
        """,
        [tenant_id],
    ).fetchall()
    parsed: list[ConditionalAccessPolicy] = []
    for row in rows:
        payload: dict[str, object] = {
            "id": row[0],
            "displayName": row[1],
            "state": row[2],
            "createdDateTime": row[3],
            "modifiedDateTime": row[4],
        }
        if row[5] is not None:
            payload["conditions"] = json.loads(row[5])
        if row[6] is not None:
            payload["grantControls"] = json.loads(row[6])
        if row[7] is not None:
            payload["sessionControls"] = json.loads(row[7])
        parsed.append(ConditionalAccessPolicy.model_validate(payload))
    return parsed
