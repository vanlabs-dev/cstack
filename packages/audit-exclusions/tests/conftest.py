from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest
from cstack_storage import get_connection, run_migrations


@pytest.fixture
def db(tmp_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    conn = get_connection(tmp_path / "audit-exclusions.duckdb")
    run_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 28, tzinfo=UTC)
