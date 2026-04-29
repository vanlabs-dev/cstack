"""Helpers that wire the audit modules to the CLI.

The CLI commands stay thin: orchestrate context load, dispatch to the right
audit module, persist findings, and print summaries. The actual rule logic
lives in the audit-* packages.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from cstack_audit_core import Finding, Severity, write_findings
from cstack_audit_coverage import compute_coverage, findings_from_coverage
from cstack_audit_exclusions import analyse_exclusions
from cstack_audit_rules import AuditContext, load_context_from_db, run_all_rules
from cstack_llm_narrative import BatchResult, NarrativeBudget, NarrativeGenerator
from cstack_llm_provider import get_provider
from cstack_llm_provider import get_settings as get_llm_settings
from cstack_schemas import TenantConfig
from cstack_storage import register_tenant, run_migrations


def open_audit_db(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Connect to the cstack DuckDB and run migrations on the way in."""
    conn = duckdb.connect(str(db_path))
    run_migrations(conn)
    return conn


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


@dataclass
class NarrativePassConfig:
    enabled: bool = True
    budget_usd: float = 1.0
    prompt_version: str = "v1"
    model: str | None = None


def narrative_config_from_env(
    *,
    override_enabled: bool | None = None,
    override_budget: float | None = None,
) -> NarrativePassConfig:
    """Resolve narrative pass settings from env, with CLI overrides."""

    settings = get_llm_settings()
    enabled = (
        override_enabled if override_enabled is not None else settings.cstack_llm_narrative_enabled
    )
    budget = override_budget if override_budget is not None else settings.cstack_llm_budget_usd
    return NarrativePassConfig(
        enabled=bool(enabled),
        budget_usd=float(budget),
        prompt_version="v1",
        model=settings.cstack_llm_default_model,
    )


def run_narrative_pass(
    conn: duckdb.DuckDBPyConnection,
    findings: list[Finding],
    config: NarrativePassConfig,
) -> BatchResult | None:
    """Generate narratives for the given findings. Returns None when the pass
    is disabled (env or no findings to narrate).
    """

    if not config.enabled or not findings:
        return None
    settings = get_llm_settings()
    provider = get_provider(settings.cstack_llm_provider)
    budget = NarrativeBudget(max_dollars=config.budget_usd)
    generator = NarrativeGenerator(
        provider=provider,
        connection=conn,
        budget=budget,
        default_model=config.model or settings.cstack_llm_default_model,
    )
    return asyncio.run(
        generator.generate_batch(
            findings,
            prompt_version=config.prompt_version,
            model=config.model,
        )
    )


def format_narrative_summary(result: BatchResult | None) -> str:
    if result is None:
        return "narratives: skipped"
    return (
        f"narratives: {result.generated} generated, {result.cache_hits} cached, "
        f"{result.skipped_budget} skipped (budget), {result.errored} errored, "
        f"${result.dollars_spent:.4f} spent"
    )
