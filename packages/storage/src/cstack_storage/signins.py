import json
from datetime import UTC, datetime

import duckdb
from cstack_schemas import SignIn


def upsert_signins(conn: duckdb.DuckDBPyConnection, tenant_id: str, signins: list[SignIn]) -> int:
    """Insert or replace sign-in rows. Returns rows written."""
    if not signins:
        return 0
    now = datetime.now(UTC)
    rows: list[tuple[object, ...]] = []
    for s in signins:
        loc = s.location
        coords = loc.geo_coordinates if loc is not None else None
        device = s.device_detail
        status = s.status
        rows.append(
            (
                tenant_id,
                s.id,
                s.user_id,
                s.user_principal_name,
                s.created_date_time,
                s.app_id,
                s.app_display_name,
                s.client_app_used,
                s.ip_address,
                loc.country_or_region if loc is not None else None,
                loc.city if loc is not None else None,
                coords.latitude if coords is not None else None,
                coords.longitude if coords is not None else None,
                device.device_id if device is not None else None,
                device.operating_system if device is not None else None,
                device.browser if device is not None else None,
                device.is_managed if device is not None else None,
                device.is_compliant if device is not None else None,
                device.trust_type if device is not None else None,
                status.error_code if status is not None else None,
                status.failure_reason if status is not None else None,
                s.conditional_access_status,
                s.authentication_requirement,
                json.dumps(s.authentication_methods_used)
                if s.authentication_methods_used is not None
                else None,
                s.risk_level_aggregated,
                s.risk_level_during_signin,
                s.risk_state,
                s.is_interactive,
                s.model_dump_json(by_alias=True, exclude_none=True),
                now,
            )
        )
    conn.executemany(
        """
        INSERT OR REPLACE INTO signins (
            tenant_id, id, user_id, user_principal_name, created_date_time,
            app_id, app_display_name, client_app_used, ip_address,
            country_or_region, city, latitude, longitude,
            device_id, device_os, device_browser, device_is_managed,
            device_is_compliant, device_trust_type,
            error_code, failure_reason, conditional_access_status,
            authentication_requirement, authentication_methods_used,
            risk_level_aggregated, risk_level_during_signin, risk_state,
            is_interactive, raw_payload, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def get_signins(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    user_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[SignIn]:
    """Read sign-ins for a tenant, optionally narrowed by user and time."""
    sql_parts = ["SELECT raw_payload FROM signins WHERE tenant_id = ?"]
    params: list[object] = [tenant_id]
    if user_id is not None:
        sql_parts.append(" AND user_id = ?")
        params.append(user_id)
    if since is not None:
        sql_parts.append(" AND created_date_time >= ?")
        params.append(since)
    if until is not None:
        sql_parts.append(" AND created_date_time <= ?")
        params.append(until)
    sql_parts.append(" ORDER BY created_date_time")
    rows = conn.execute("".join(sql_parts), params).fetchall()
    return [SignIn.model_validate(json.loads(r[0])) for r in rows]


def count_signins_by_user(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT user_id, COUNT(*) FROM signins WHERE tenant_id = ? GROUP BY user_id",
        [tenant_id],
    ).fetchall()
    return {row[0]: int(row[1]) for row in rows}
