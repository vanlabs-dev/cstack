"""Application lifespan: startup, shutdown, shared state.

DuckDB connections are not safe to share across concurrent writers, so the
lifespan only stores a connection-factory and the resolved settings on
``app.state``. Each request acquires a fresh connection through the
``get_db_connection`` dependency.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import duckdb
from cstack_storage import connection_scope, run_migrations
from fastapi import FastAPI

from signalguard_api.config import Settings, get_settings
from signalguard_api.logging_setup import configure_logging

LOG = logging.getLogger(__name__)


def _ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connection_scope(db_path) as conn:
        run_migrations(conn)


def _connection_factory(db_path: Path) -> Callable[[], duckdb.DuckDBPyConnection]:
    """Return a callable that opens a fresh DuckDB connection on each call."""

    def _open() -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(db_path))

    return _open


def _configure_mlflow(uri: str | None) -> None:
    """Honour an explicit MLflow URI override before any router needs it."""
    if uri is None:
        return
    from cstack_ml_mlops import configure_tracking

    configure_tracking(uri=uri)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Wire startup and shutdown work to the FastAPI app lifecycle."""
    settings: Settings = app.state.settings if hasattr(app.state, "settings") else get_settings()
    configure_logging(settings.log_level)
    LOG.info(
        "signalguard-api starting",
        extra={"db_path": str(settings.db_path), "log_level": settings.log_level},
    )
    _ensure_db(settings.db_path)
    _configure_mlflow(settings.mlflow_tracking_uri)

    app.state.settings = settings
    app.state.connection_factory = _connection_factory(settings.db_path)
    try:
        yield
    finally:
        LOG.info("signalguard-api shutting down")
        for handler in logging.getLogger().handlers:
            handler.flush()
