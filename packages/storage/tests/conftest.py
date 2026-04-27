from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from cstack_storage import get_connection, run_migrations


@pytest.fixture
def db(tmp_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """A migrated DuckDB connection backed by a per-test temp file."""
    conn = get_connection(tmp_path / "test.duckdb")
    run_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()
