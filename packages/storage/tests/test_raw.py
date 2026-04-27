import duckdb
from cstack_storage import latest_raw, write_raw


def test_write_and_read_latest(db: duckdb.DuckDBPyConnection) -> None:
    payload = [{"id": "p1", "displayName": "policy 1"}]
    write_raw(db, "tenant-x", "ca-policies", payload, source_path="memory://test")
    fetched = latest_raw(db, "tenant-x", "ca-policies")
    assert fetched == payload


def test_latest_returns_most_recent(db: duckdb.DuckDBPyConnection) -> None:
    write_raw(db, "tenant-x", "ca-policies", [{"id": "v1"}])
    write_raw(db, "tenant-x", "ca-policies", [{"id": "v2"}])
    assert latest_raw(db, "tenant-x", "ca-policies") == [{"id": "v2"}]


def test_latest_none_when_empty(db: duckdb.DuckDBPyConnection) -> None:
    assert latest_raw(db, "tenant-x", "ca-policies") is None
