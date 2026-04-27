import json
from datetime import UTC, datetime
from typing import Any

import duckdb


def write_raw(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    resource_type: str,
    payload: object,
    source_path: str | None = None,
) -> None:
    """Append a raw Graph payload snapshot to ``raw_ingestions``.

    The raw layer keeps original responses verbatim so we can replay parsing
    logic against historical pulls when schema mappings change.
    """
    conn.execute(
        """
        INSERT INTO raw_ingestions
            (tenant_id, resource_type, ingested_at, raw_payload, source_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            tenant_id,
            resource_type,
            datetime.now(UTC),
            json.dumps(payload, default=str),
            source_path,
        ],
    )


def latest_raw(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    resource_type: str,
) -> Any:
    """Return the most-recent raw payload for the given tenant and resource.

    Returns ``None`` when no ingestion exists yet. The shape of the returned
    object mirrors whatever was passed to :func:`write_raw` (typically a list
    or dict).
    """
    row = conn.execute(
        """
        SELECT raw_payload FROM raw_ingestions
        WHERE tenant_id = ? AND resource_type = ?
        ORDER BY ingested_at DESC LIMIT 1
        """,
        [tenant_id, resource_type],
    ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])
