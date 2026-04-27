import duckdb
from cstack_schemas import TenantConfig


def register_tenant(conn: duckdb.DuckDBPyConnection, tenant: TenantConfig) -> None:
    """Idempotently upsert a tenant row.

    Used by both the live extract path and the fixtures loader so any tenant
    with stored data is queryable from SQL.
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO tenants
            (tenant_id, display_name, client_id, cert_thumbprint, cert_subject,
             added_at, is_fixture)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            tenant.tenant_id,
            tenant.display_name,
            tenant.client_id,
            tenant.cert_thumbprint,
            tenant.cert_subject,
            tenant.added_at,
            tenant.is_fixture,
        ],
    )


def list_tenants_db(conn: duckdb.DuckDBPyConnection) -> list[TenantConfig]:
    rows = conn.execute(
        """
        SELECT tenant_id, display_name, client_id, cert_thumbprint, cert_subject,
               added_at, is_fixture
        FROM tenants
        ORDER BY display_name
        """
    ).fetchall()
    return [
        TenantConfig(
            tenant_id=row[0],
            display_name=row[1],
            client_id=row[2],
            cert_thumbprint=row[3],
            cert_subject=row[4],
            added_at=row[5],
            is_fixture=row[6],
        )
        for row in rows
    ]


def get_tenant_db(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> TenantConfig | None:
    row = conn.execute(
        """
        SELECT tenant_id, display_name, client_id, cert_thumbprint, cert_subject,
               added_at, is_fixture
        FROM tenants WHERE tenant_id = ?
        """,
        [tenant_id],
    ).fetchone()
    if row is None:
        return None
    return TenantConfig(
        tenant_id=row[0],
        display_name=row[1],
        client_id=row[2],
        cert_thumbprint=row[3],
        cert_subject=row[4],
        added_at=row[5],
        is_fixture=row[6],
    )


def remove_tenant_db(conn: duckdb.DuckDBPyConnection, tenant_id: str) -> None:
    """Delete a tenant row plus any data rows scoped to it."""
    for table in (
        "ca_policies",
        "named_locations",
        "users",
        "groups",
        "directory_roles",
        "role_assignments",
        "raw_ingestions",
        "tenants",
    ):
        conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", [tenant_id])
