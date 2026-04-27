from pathlib import Path

from cstack_storage import MIGRATIONS, get_connection, run_migrations


def test_run_migrations_creates_expected_tables(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "x.duckdb")
    applied = run_migrations(conn)
    assert applied == [m.version for m in MIGRATIONS]
    tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    expected = {
        "_migrations",
        "tenants",
        "raw_ingestions",
        "ca_policies",
        "named_locations",
        "users",
        "groups",
        "directory_roles",
        "role_assignments",
    }
    assert expected.issubset(tables)


def test_run_migrations_is_idempotent(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "x.duckdb")
    first = run_migrations(conn)
    second = run_migrations(conn)
    assert first  # at least one applied on the first run
    assert second == []  # nothing left to apply on the second run
