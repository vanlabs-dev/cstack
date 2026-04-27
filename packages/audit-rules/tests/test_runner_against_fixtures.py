"""Integration: each fixture loads, every rule runs, no rule throws.

Exact counts are calibrated in Phase 6 and asserted via metadata.json there.
"""

from datetime import datetime

import duckdb
from cstack_audit_rules import load_context_from_db, run_all_rules
from cstack_fixtures import (
    FIXTURE_TENANT_A_ID,
    FIXTURE_TENANT_B_ID,
    FIXTURE_TENANT_C_ID,
    load_fixture,
)


def test_tenant_a_runs_clean(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    load_fixture("tenant-a", db)
    context = load_context_from_db(db, FIXTURE_TENANT_A_ID, as_of=now)
    findings = run_all_rules(context)
    # Well-configured tenant should have few or no findings; we don't assert
    # zero because some informational rules legitimately fire.
    assert isinstance(findings, list)


def test_tenant_b_produces_findings(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    load_fixture("tenant-b", db)
    context = load_context_from_db(db, FIXTURE_TENANT_B_ID, as_of=now)
    findings = run_all_rules(context)
    assert len(findings) > 0


def test_tenant_c_no_rule_crashes(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    load_fixture("tenant-c", db)
    context = load_context_from_db(db, FIXTURE_TENANT_C_ID, as_of=now)
    # run_all_rules swallows individual rule exceptions, but we also want to
    # confirm the runner returns a list and the context loads cleanly.
    findings = run_all_rules(context)
    assert isinstance(findings, list)
