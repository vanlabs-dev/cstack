"""Integration tests: each fixture's exclusions analyse without errors."""

from datetime import datetime

import duckdb
from cstack_audit_exclusions import analyse_exclusions
from cstack_audit_rules import load_context_from_db
from cstack_fixtures import (
    FIXTURE_TENANT_A_ID,
    FIXTURE_TENANT_B_ID,
    FIXTURE_TENANT_C_ID,
    load_fixture,
)


def test_tenant_a_analyses(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    load_fixture("tenant-a", db)
    context = load_context_from_db(db, FIXTURE_TENANT_A_ID, as_of=now)
    findings = analyse_exclusions(context)
    assert isinstance(findings, list)


def test_tenant_b_produces_findings(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    load_fixture("tenant-b", db)
    context = load_context_from_db(db, FIXTURE_TENANT_B_ID, as_of=now)
    findings = analyse_exclusions(context)
    # tenant-b's "messy" scenario lists 14 user exclusions on one policy, so
    # the analyser should produce at least an exclusion.creep finding.
    assert any(f.rule_id == "exclusion.creep" for f in findings)


def test_tenant_c_no_crashes(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    load_fixture("tenant-c", db)
    context = load_context_from_db(db, FIXTURE_TENANT_C_ID, as_of=now)
    analyse_exclusions(context)  # must not raise
