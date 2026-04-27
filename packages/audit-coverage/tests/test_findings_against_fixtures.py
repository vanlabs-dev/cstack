"""Integration tests: load each bundled fixture and exercise coverage.

Expected counts come from each fixture's ``metadata.json`` (calibrated in
Sprint 2). When a fixture or a rule changes, re-run ``cstack audit all``
against the fixture and update its metadata, then this test stays current.
"""

import json
from datetime import UTC, datetime

import duckdb
from cstack_audit_coverage import compute_coverage, findings_from_coverage
from cstack_fixtures import list_fixtures, load_fixture
from cstack_schemas import (
    ConditionalAccessPolicy,
    DirectoryRole,
    Group,
    User,
)


def _hydrated_inputs(
    db: duckdb.DuckDBPyConnection, tenant_id: str
) -> tuple[list[ConditionalAccessPolicy], list[User], list[Group], list[DirectoryRole]]:
    from cstack_storage import get_policies

    policies = get_policies(db, tenant_id)
    user_rows = db.execute("SELECT raw FROM users WHERE tenant_id = ?", [tenant_id]).fetchall()
    group_rows = db.execute("SELECT raw FROM groups WHERE tenant_id = ?", [tenant_id]).fetchall()
    role_rows = db.execute(
        "SELECT raw FROM directory_roles WHERE tenant_id = ?", [tenant_id]
    ).fetchall()
    users = [User.model_validate(json.loads(r[0])) for r in user_rows]
    groups = [Group.model_validate(json.loads(r[0])) for r in group_rows]
    roles = [DirectoryRole.model_validate(json.loads(r[0])) for r in role_rows]
    return policies, users, groups, roles


def _expected_for(fixture_name: str) -> dict[str, int]:
    metas = {m.name: m for m in list_fixtures()}
    return metas[fixture_name].expected_findings.by_category


def _coverage_count_for(name: str, db: duckdb.DuckDBPyConnection) -> int:
    metas = {m.name: m for m in list_fixtures()}
    tenant_id = metas[name].tenant_id
    load_fixture(name, db)
    policies, users, groups, roles = _hydrated_inputs(db, tenant_id)
    matrix = compute_coverage(
        tenant_id,
        policies,
        users,
        groups,
        roles,
        [],
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )
    return len(findings_from_coverage(matrix, tenant_id))


def test_tenant_a_matches_calibrated_coverage(db: duckdb.DuckDBPyConnection) -> None:
    expected = _expected_for("tenant-a")["coverage"]
    assert _coverage_count_for("tenant-a", db) == expected


def test_tenant_b_matches_calibrated_coverage(db: duckdb.DuckDBPyConnection) -> None:
    expected = _expected_for("tenant-b")["coverage"]
    assert _coverage_count_for("tenant-b", db) == expected


def test_tenant_c_matches_calibrated_coverage(db: duckdb.DuckDBPyConnection) -> None:
    expected = _expected_for("tenant-c")["coverage"]
    assert _coverage_count_for("tenant-c", db) == expected
