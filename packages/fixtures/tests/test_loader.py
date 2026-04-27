import duckdb
from cstack_fixtures import (
    FIXTURE_TENANT_A_ID,
    FIXTURE_TENANT_B_ID,
    FIXTURE_TENANT_C_ID,
    clear_fixture,
    list_fixtures,
    load_fixture,
)

ALL_FIXTURE_NAMES = ["tenant-a", "tenant-b", "tenant-c"]


def test_list_fixtures_returns_all_three() -> None:
    metas = list_fixtures()
    names = [m.name for m in metas]
    assert sorted(names) == sorted(ALL_FIXTURE_NAMES)


def test_load_fixture_populates_rows(db: duckdb.DuckDBPyConnection) -> None:
    result = load_fixture("tenant-a", db)
    assert result.tenant_id == FIXTURE_TENANT_A_ID
    assert result.counts["ca_policies"] == 8
    assert result.counts["named_locations"] == 3
    assert result.counts["users"] == 60
    assert result.counts["groups"] == 12
    assert result.counts["directory_roles"] == 8

    rows = db.execute(
        "SELECT COUNT(*) FROM ca_policies WHERE tenant_id = ?", [FIXTURE_TENANT_A_ID]
    ).fetchone()
    assert rows is not None
    assert rows[0] == 8


def test_load_fixture_is_idempotent(db: duckdb.DuckDBPyConnection) -> None:
    first = load_fixture("tenant-b", db)
    second = load_fixture("tenant-b", db)
    assert first.counts == second.counts

    rows = db.execute(
        "SELECT COUNT(*) FROM ca_policies WHERE tenant_id = ?", [FIXTURE_TENANT_B_ID]
    ).fetchone()
    assert rows is not None
    assert rows[0] == first.counts["ca_policies"]


def test_clear_fixture_only_targets_one_tenant(db: duckdb.DuckDBPyConnection) -> None:
    load_fixture("tenant-a", db)
    load_fixture("tenant-b", db)
    clear_fixture("tenant-a", db)

    a_count = db.execute(
        "SELECT COUNT(*) FROM ca_policies WHERE tenant_id = ?", [FIXTURE_TENANT_A_ID]
    ).fetchone()
    b_count = db.execute(
        "SELECT COUNT(*) FROM ca_policies WHERE tenant_id = ?", [FIXTURE_TENANT_B_ID]
    ).fetchone()
    assert a_count is not None and b_count is not None
    assert a_count[0] == 0
    assert b_count[0] > 0


def test_all_three_fixtures_parse_cleanly(db: duckdb.DuckDBPyConnection) -> None:
    """Catches schema drift: every fixture must load through pydantic without error."""
    for name in ALL_FIXTURE_NAMES:
        result = load_fixture(name, db)
        assert result.counts["ca_policies"] > 0
        assert result.counts["users"] > 0

    rows = db.execute("SELECT DISTINCT tenant_id FROM tenants ORDER BY tenant_id").fetchall()
    assert {r[0] for r in rows} == {
        FIXTURE_TENANT_A_ID,
        FIXTURE_TENANT_B_ID,
        FIXTURE_TENANT_C_ID,
    }
