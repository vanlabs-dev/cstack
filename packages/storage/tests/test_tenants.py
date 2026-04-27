from datetime import UTC, datetime

import duckdb
from cstack_schemas import TenantConfig
from cstack_storage import (
    get_tenant_db,
    list_tenants_db,
    register_tenant,
    remove_tenant_db,
)


def _make(tenant_id: str, name: str, is_fixture: bool = False) -> TenantConfig:
    return TenantConfig(
        tenant_id=tenant_id,
        display_name=name,
        client_id="00000000-0000-0000-0000-000000000099",
        cert_thumbprint="A" * 40,
        cert_subject="CN=cstack",
        added_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_fixture=is_fixture,
    )


def test_register_and_list(db: duckdb.DuckDBPyConnection) -> None:
    register_tenant(db, _make("00000000-0000-0000-0000-000000000001", "alpha"))
    register_tenant(db, _make("00000000-0000-0000-0000-000000000002", "beta", is_fixture=True))
    tenants = list_tenants_db(db)
    assert [t.display_name for t in tenants] == ["alpha", "beta"]
    assert [t.is_fixture for t in tenants] == [False, True]


def test_register_is_idempotent(db: duckdb.DuckDBPyConnection) -> None:
    tid = "00000000-0000-0000-0000-000000000001"
    register_tenant(db, _make(tid, "v1"))
    register_tenant(db, _make(tid, "v2"))
    fetched = get_tenant_db(db, tid)
    assert fetched is not None
    assert fetched.display_name == "v2"


def test_remove_clears_only_target(db: duckdb.DuckDBPyConnection) -> None:
    keep = "00000000-0000-0000-0000-000000000001"
    drop = "00000000-0000-0000-0000-000000000002"
    register_tenant(db, _make(keep, "keep"))
    register_tenant(db, _make(drop, "drop"))
    remove_tenant_db(db, drop)
    remaining = list_tenants_db(db)
    assert [t.tenant_id for t in remaining] == [keep]
