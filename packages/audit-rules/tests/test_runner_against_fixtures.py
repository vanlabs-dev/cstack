"""Integration tests: rule runner against each bundled fixture.

Expected counts come from ``metadata.json``, which is calibrated against the
audit engine. Re-run ``cstack audit all`` against the fixture and update the
metadata file when expectations change.
"""

from datetime import datetime

import duckdb
from cstack_audit_rules import load_context_from_db, run_all_rules
from cstack_fixtures import list_fixtures, load_fixture


def _expected(fixture_name: str) -> int:
    metas = {m.name: m for m in list_fixtures()}
    return metas[fixture_name].expected_findings.by_category.get("rule", 0)


def _run(fixture_name: str, db: duckdb.DuckDBPyConnection, now: datetime) -> int:
    metas = {m.name: m for m in list_fixtures()}
    tenant_id = metas[fixture_name].tenant_id
    load_fixture(fixture_name, db)
    context = load_context_from_db(db, tenant_id, as_of=now)
    return len(run_all_rules(context))


def test_tenant_a_rules_match_calibration(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    assert _run("tenant-a", db, now) == _expected("tenant-a")


def test_tenant_b_rules_match_calibration(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    assert _run("tenant-b", db, now) == _expected("tenant-b")


def test_tenant_c_rules_match_calibration(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    assert _run("tenant-c", db, now) == _expected("tenant-c")
