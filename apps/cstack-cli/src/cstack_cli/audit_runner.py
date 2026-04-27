"""Helpers that wire the audit modules to the CLI.

The CLI commands stay thin: orchestrate context load, dispatch to the right
audit module, persist findings, and print summaries. The actual rule logic
lives in the audit-* packages.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from cstack_audit_core import Finding, Severity, write_findings
from cstack_audit_coverage import compute_coverage, findings_from_coverage
from cstack_audit_exclusions import analyse_exclusions
from cstack_audit_rules import AuditContext, load_context_from_db, run_all_rules
from cstack_schemas import TenantConfig
from cstack_storage import (
    connection_scope,
    list_tenants_db,
    register_tenant,
    run_migrations,
)


def open_audit_db(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Connect to the cstack DuckDB and run migrations on the way in."""
    conn = duckdb.connect(str(db_path))
    run_migrations(conn)
    return conn


def resolve_tenant_for_audit(
    db_path: Path,
    tenants_file: Path,
    identifier: str,
    file_loader: object,
) -> TenantConfig:
    """Look up a tenant from tenants.json or the DB tenants table.

    Lazy import of the file loader is done by callers (passing in
    ``cstack_cli.tenants.load_tenants``) so this module stays free of
    cross-imports back into the CLI package.
    """
    from cstack_cli.tenants import find_tenant, load_tenants

    file_tenants = load_tenants(tenants_file)
    found = find_tenant(file_tenants, identifier)
    if found is not None:
        return found
    with connection_scope(db_path) as conn:
        run_migrations(conn)
        for tenant in list_tenants_db(conn):
            if tenant.tenant_id == identifier or tenant.display_name == identifier:
                return tenant
    raise LookupError(f"no tenant matching '{identifier}'")


def load_context(conn: duckdb.DuckDBPyConnection, tenant: TenantConfig) -> AuditContext:
    """Load an AuditContext for the tenant, registering it first if absent."""
    register_tenant(conn, tenant)
    return load_context_from_db(conn, tenant.tenant_id, as_of=datetime.now(UTC))


def run_coverage(context: AuditContext) -> list[Finding]:
    matrix = compute_coverage(
        context.tenant_id,
        context.policies,
        context.users,
        context.groups,
        context.roles,
        context.role_assignments,
        as_of=context.as_of,
    )
    return findings_from_coverage(matrix, context.tenant_id)


def run_rules(context: AuditContext) -> list[Finding]:
    return run_all_rules(context)


def run_exclusions(context: AuditContext) -> list[Finding]:
    return analyse_exclusions(context)


def persist(conn: duckdb.DuckDBPyConnection, findings: list[Finding]) -> int:
    return write_findings(conn, findings)


def severity_breakdown(findings: list[Finding]) -> dict[str, int]:
    """Count findings per severity, lowercased keys for table-friendly output."""
    counter: Counter[str] = Counter()
    for f in findings:
        counter[f.severity.value.lower()] += 1
    return {sev: counter.get(sev, 0) for sev in ("critical", "high", "medium", "low", "info")}


def format_summary(name: str, breakdowns: dict[str, dict[str, int]]) -> str:
    """Format a per-category breakdown table for stdout."""
    lines = [f"tenant: {name}"]
    total = 0
    for category, counts in breakdowns.items():
        cat_total = sum(counts.values())
        total += cat_total
        formatted = ", ".join(f"{k}: {v}" for k, v in counts.items())
        lines.append(f"  {category:<11} {cat_total:>3} findings  ({formatted})")
    lines.append(f"  {'total':<11} {total:>3} findings")
    return "\n".join(lines)


def parse_severity(value: str | None) -> Severity | None:
    if value is None:
        return None
    return Severity(value.upper())
