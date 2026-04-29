from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest
from cstack_audit_core import AffectedObject, Finding, Severity
from cstack_storage import run_migrations


@pytest.fixture
def db(tmp_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    conn = duckdb.connect(str(tmp_path / "eval.duckdb"))
    run_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def finding() -> Finding:
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    return Finding(
        id="f-1",
        tenant_id="tenant-b",
        rule_id="rule.block-legacy-auth",
        category="rule",
        severity=Severity.HIGH,
        title="Block legacy authentication",
        summary="No enabled CA policy blocks legacy authentication.",
        affected_objects=[AffectedObject(type="tenant", id="tenant-b", display_name="tenant-b")],
        evidence={"policies_targeting_legacy_auth": 0},
        remediation_hint="Add an enabled CA policy that blocks legacy auth.",
        references=["https://learn.microsoft.com/x"],
        detected_at=now,
        first_seen_at=now,
    )
