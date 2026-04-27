from datetime import datetime

import duckdb
from cstack_audit_core import (
    AffectedObject,
    Finding,
    Severity,
    findings_by_rule,
    latest_findings,
    write_findings,
)

TENANT = "00000000-0000-0000-0000-aaaaaaaaaaaa"


def _finding(
    rule_id: str,
    severity: Severity,
    affected_ids: list[str],
    now: datetime,
    category: str = "rule",
) -> Finding:
    return Finding(
        id=Finding.compute_id(TENANT, rule_id, affected_ids),
        tenant_id=TENANT,
        rule_id=rule_id,
        category=category,  # type: ignore[arg-type]
        severity=severity,
        title=f"{rule_id} fired",
        summary="example",
        affected_objects=[
            AffectedObject(type="policy", id=oid, display_name=f"obj {oid}") for oid in affected_ids
        ],
        evidence={"reason": "test"},
        remediation_hint="do the thing",
        references=["https://example.test/ref"],
        detected_at=now,
        first_seen_at=now,
    )


def test_roundtrip(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    finding = _finding("rule.x", Severity.HIGH, ["obj-1"], now)
    inserted = write_findings(db, [finding])
    assert inserted == 1

    fetched = latest_findings(db, TENANT)
    assert len(fetched) == 1
    assert fetched[0].id == finding.id
    assert fetched[0].severity == Severity.HIGH
    assert fetched[0].affected_objects[0].id == "obj-1"


def test_dedupe_on_repeated_writes(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    finding = _finding("rule.dup", Severity.MEDIUM, ["o1"], now)
    assert write_findings(db, [finding]) == 1
    assert write_findings(db, [finding]) == 0
    assert len(latest_findings(db, TENANT)) == 1


def test_filter_by_category(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    write_findings(
        db,
        [
            _finding("rule.r1", Severity.LOW, ["o1"], now, category="rule"),
            _finding("coverage.c1", Severity.HIGH, ["o2"], now, category="coverage"),
            _finding("exclusion.e1", Severity.MEDIUM, ["o3"], now, category="exclusion"),
        ],
    )
    rule_only = latest_findings(db, TENANT, category="rule")
    assert {f.rule_id for f in rule_only} == {"rule.r1"}


def test_filter_by_min_severity(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    write_findings(
        db,
        [
            _finding("rule.r1", Severity.LOW, ["o1"], now),
            _finding("rule.r2", Severity.HIGH, ["o2"], now),
            _finding("rule.r3", Severity.CRITICAL, ["o3"], now),
        ],
    )
    high_or_above = latest_findings(db, TENANT, min_severity=Severity.HIGH)
    assert {f.severity for f in high_or_above} == {Severity.HIGH, Severity.CRITICAL}


def test_filter_by_rule_id(db: duckdb.DuckDBPyConnection, now: datetime) -> None:
    write_findings(
        db,
        [
            _finding("rule.r1", Severity.LOW, ["o1"], now),
            _finding("rule.r2", Severity.LOW, ["o2"], now),
        ],
    )
    only_r1 = findings_by_rule(db, TENANT, "rule.r1")
    assert len(only_r1) == 1
    assert only_r1[0].rule_id == "rule.r1"
