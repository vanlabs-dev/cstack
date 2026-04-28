"""FastAPI dependencies: per-request DB connection and tenant resolver.

Each request gets its own DuckDB connection because DuckDB connections do
not handle concurrent writers from multiple threads cleanly, and FastAPI's
default thread pool dispatches sync work onto a worker pool.
"""

from __future__ import annotations

from collections.abc import Iterator

import duckdb
from cstack_schemas import TenantConfig
from cstack_storage import get_tenant_db, run_migrations
from fastapi import Depends, HTTPException, Request, status

from signalguard_api.config import Settings, get_settings


def get_db_connection(request: Request) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a fresh DuckDB connection sourced from the lifespan factory."""
    factory = request.app.state.connection_factory
    conn: duckdb.DuckDBPyConnection = factory()
    try:
        run_migrations(conn)
        yield conn
    finally:
        conn.close()


def get_tenant(
    tenant_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_db_connection),
) -> TenantConfig:
    tenant = get_tenant_db(conn, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"tenant '{tenant_id}' not registered",
        )
    return tenant


def resolved_settings(settings: Settings = Depends(get_settings)) -> Settings:
    return settings
