from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open (or create) a DuckDB database file at the given path.

    Parent directories are created on demand because the typical install
    runs the CLI from a fresh checkout where ``data/`` does not yet exist.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


@contextmanager
def connection_scope(db_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Context manager that closes the DuckDB connection on exit."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
