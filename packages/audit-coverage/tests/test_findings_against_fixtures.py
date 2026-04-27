"""Integration tests: load each bundled fixture and exercise coverage.

These tests assert that each fixture loads, the matrix builds without
exceptions, and broad shape expectations hold. Exact finding counts are
calibrated in the Phase 6 sprint loop and asserted via metadata.json there.
"""

from datetime import UTC, datetime

import duckdb
from cstack_audit_core import Severity
from cstack_audit_coverage import (
    compute_coverage,
    findings_from_coverage,
)
from cstack_fixtures import (
    FIXTURE_TENANT_A_ID,
    FIXTURE_TENANT_B_ID,
    FIXTURE_TENANT_C_ID,
    load_fixture,
)
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
    import json

    users = [User.model_validate(json.loads(r[0])) for r in user_rows]
    groups = [Group.model_validate(json.loads(r[0])) for r in group_rows]
    roles = [DirectoryRole.model_validate(json.loads(r[0])) for r in role_rows]
    return policies, users, groups, roles


def test_tenant_a_has_no_critical_coverage_findings(db: duckdb.DuckDBPyConnection) -> None:
    load_fixture("tenant-a", db)
    policies, users, groups, roles = _hydrated_inputs(db, FIXTURE_TENANT_A_ID)
    matrix = compute_coverage(
        FIXTURE_TENANT_A_ID,
        policies,
        users,
        groups,
        roles,
        [],
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )
    findings = findings_from_coverage(matrix, FIXTURE_TENANT_A_ID)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    # Without role members in fixture data, ADMINS_ANY and PRIVILEGED_ROLES
    # segments are empty; well-configured tenant-a should not produce CRITICAL
    # cells from non-empty segments either.
    assert critical == []


def test_tenant_b_produces_findings(db: duckdb.DuckDBPyConnection) -> None:
    load_fixture("tenant-b", db)
    policies, users, groups, roles = _hydrated_inputs(db, FIXTURE_TENANT_B_ID)
    matrix = compute_coverage(
        FIXTURE_TENANT_B_ID,
        policies,
        users,
        groups,
        roles,
        [],
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )
    findings = findings_from_coverage(matrix, FIXTURE_TENANT_B_ID)
    # tenant-b has gaps; expect at least some findings to fire.
    assert len(findings) > 0


def test_tenant_c_does_not_crash(db: duckdb.DuckDBPyConnection) -> None:
    load_fixture("tenant-c", db)
    policies, users, groups, roles = _hydrated_inputs(db, FIXTURE_TENANT_C_ID)
    matrix = compute_coverage(
        FIXTURE_TENANT_C_ID,
        policies,
        users,
        groups,
        roles,
        [],
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )
    findings_from_coverage(matrix, FIXTURE_TENANT_C_ID)  # must not raise
