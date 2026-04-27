from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import cast

import click
from cstack_fixtures import (
    clear_all_fixtures as fixtures_clear_all_helper,
)
from cstack_fixtures import (
    clear_fixture as fixtures_clear_helper,
)
from cstack_fixtures import (
    list_fixtures as fixtures_list_helper,
)
from cstack_fixtures import (
    load_fixture as fixtures_load_helper,
)
from cstack_graph_client import build_client, load_certificate_credential
from cstack_schemas import TenantConfig
from cstack_storage import (
    connection_scope,
    list_tenants_db,
    register_tenant,
    remove_tenant_db,
    run_migrations,
)

from cstack_cli.config import Settings
from cstack_cli.extract import (
    extract_ca_policies,
    extract_directory,
    extract_named_locations,
)
from cstack_cli.logging_setup import configure_logging
from cstack_cli.tenants import find_tenant, load_tenants, save_tenants

LOG = logging.getLogger(__name__)


def _settings(ctx: click.Context) -> Settings:
    return cast(Settings, ctx.obj["settings"])


def _resolve_tenant(ctx: click.Context, identifier: str) -> TenantConfig:
    """Look up a tenant by tenant_id or display_name across both stores."""
    settings = _settings(ctx)
    file_tenants = load_tenants(settings.tenants_file)
    found = find_tenant(file_tenants, identifier)
    if found is not None:
        return found

    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        for tenant in list_tenants_db(conn):
            if tenant.tenant_id == identifier or tenant.display_name == identifier:
                return tenant
    raise click.ClickException(f"no tenant matching '{identifier}'")


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """cstack: tooling for Microsoft 365 tenant operations."""
    ctx.ensure_object(dict)
    settings = Settings()
    configure_logging(settings.log_level)
    ctx.obj["settings"] = settings


# --- tenant subgroup -----------------------------------------------------


@cli.group()
def tenant() -> None:
    """Manage tenant registrations."""


@tenant.command("add")
@click.option("--tenant-id", required=True, prompt=True, help="Entra tenant UUID.")
@click.option("--display-name", required=True, prompt=True)
@click.option("--client-id", required=True, prompt=True, help="App registration client UUID.")
@click.option("--cert-thumbprint", required=True, prompt=True, help="SHA-1 hex.")
@click.option("--cert-subject", default="CN=cstack-signalguard", show_default=True)
@click.pass_context
def tenant_add(
    ctx: click.Context,
    tenant_id: str,
    display_name: str,
    client_id: str,
    cert_thumbprint: str,
    cert_subject: str,
) -> None:
    """Register a live tenant. Appends to tenants.json and the DB tenants table."""
    settings = _settings(ctx)
    new = TenantConfig(
        tenant_id=tenant_id,
        display_name=display_name,
        client_id=client_id,
        cert_thumbprint=cert_thumbprint,
        cert_subject=cert_subject,
        added_at=datetime.now(UTC),
        is_fixture=False,
    )
    existing = load_tenants(settings.tenants_file)
    if find_tenant(existing, tenant_id) is not None:
        raise click.ClickException(f"tenant {tenant_id} already registered")
    existing.append(new)
    save_tenants(settings.tenants_file, existing)

    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        register_tenant(conn, new)
    click.echo(f"registered tenant {display_name} ({tenant_id})")


@tenant.command("list")
@click.pass_context
def tenant_list(ctx: click.Context) -> None:
    """List registered tenants. Includes fixtures hydrated into the DB."""
    settings = _settings(ctx)

    seen: dict[str, TenantConfig] = {}
    for t in load_tenants(settings.tenants_file):
        seen[t.tenant_id] = t
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        for t in list_tenants_db(conn):
            seen.setdefault(t.tenant_id, t)

    if not seen:
        click.echo("(no tenants registered)")
        return

    rows = sorted(seen.values(), key=lambda t: t.display_name)
    name_width = max(len("display_name"), *(len(t.display_name) for t in rows))
    id_width = max(len("tenant_id"), *(len(t.tenant_id) for t in rows))
    header = f"{'display_name'.ljust(name_width)}  {'tenant_id'.ljust(id_width)}  fixture"
    click.echo(header)
    click.echo("-" * len(header))
    for t in rows:
        marker = "yes" if t.is_fixture else "no"
        click.echo(f"{t.display_name.ljust(name_width)}  {t.tenant_id.ljust(id_width)}  {marker}")


@tenant.command("remove")
@click.argument("identifier")
@click.pass_context
def tenant_remove(ctx: click.Context, identifier: str) -> None:
    """Remove a tenant from tenants.json and clear its rows from the DB."""
    settings = _settings(ctx)
    existing = load_tenants(settings.tenants_file)
    target = find_tenant(existing, identifier)
    if target is None:
        # Not in the file; check the DB and remove from there only.
        with connection_scope(settings.db_path) as conn:
            run_migrations(conn)
            for db_tenant in list_tenants_db(conn):
                if db_tenant.tenant_id == identifier or db_tenant.display_name == identifier:
                    remove_tenant_db(conn, db_tenant.tenant_id)
                    click.echo(f"removed {db_tenant.display_name} from db only")
                    return
        raise click.ClickException(f"no tenant matching '{identifier}'")
    survivors = [t for t in existing if t.tenant_id != target.tenant_id]
    save_tenants(settings.tenants_file, survivors)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        remove_tenant_db(conn, target.tenant_id)
    click.echo(f"removed {target.display_name} ({target.tenant_id})")


@tenant.command("verify")
@click.argument("identifier")
@click.pass_context
def tenant_verify(ctx: click.Context, identifier: str) -> None:
    """Run a Microsoft Graph organization call to confirm cert auth works."""
    target = _resolve_tenant(ctx, identifier)
    if target.is_fixture:
        click.echo(f"{target.display_name}: fixture tenant; skipping live verify")
        return

    async def _run() -> None:
        credential = load_certificate_credential(
            target.tenant_id, target.client_id, target.cert_thumbprint
        )
        client = build_client(credential)
        org = await client.organization.get()
        if org is None:
            raise click.ClickException("organization call returned None")
        click.echo(f"{target.display_name}: graph auth ok")

    asyncio.run(_run())


# --- extract subgroup ----------------------------------------------------


@cli.group()
def extract() -> None:
    """Pull Graph data into the cstack store."""


def _ensure_paths(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)


@extract.command("ca-policies")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def extract_ca_policies_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    settings = _settings(ctx)
    _ensure_paths(settings)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        register_tenant(conn, target)
        count = extract_ca_policies(conn, target, settings.data_dir)
    click.echo(f"{target.display_name}: ca-policies upserted={count}")


@extract.command("named-locations")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def extract_named_locations_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    settings = _settings(ctx)
    _ensure_paths(settings)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        register_tenant(conn, target)
        count = extract_named_locations(conn, target, settings.data_dir)
    click.echo(f"{target.display_name}: named-locations upserted={count}")


@extract.command("directory")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def extract_directory_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    settings = _settings(ctx)
    _ensure_paths(settings)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        register_tenant(conn, target)
        counts = extract_directory(conn, target, settings.data_dir)
    formatted = ", ".join(f"{k}={v}" for k, v in counts.items())
    click.echo(f"{target.display_name}: {formatted}")


@extract.command("all")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def extract_all_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    settings = _settings(ctx)
    _ensure_paths(settings)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        register_tenant(conn, target)
        ca_count = extract_ca_policies(conn, target, settings.data_dir)
        loc_count = extract_named_locations(conn, target, settings.data_dir)
        dir_counts = extract_directory(conn, target, settings.data_dir)
    parts = [f"ca_policies={ca_count}", f"named_locations={loc_count}"]
    parts.extend(f"{k}={v}" for k, v in dir_counts.items())
    click.echo(f"{target.display_name}: " + ", ".join(parts))


# --- fixtures subgroup ---------------------------------------------------


@cli.group()
def fixtures() -> None:
    """Manage synthetic fixture tenants for offline development."""


@fixtures.command("list")
def fixtures_list_cmd() -> None:
    metas = fixtures_list_helper()
    if not metas:
        click.echo("(no fixtures bundled)")
        return
    name_width = max(len("name"), *(len(m.name) for m in metas))
    click.echo(f"{'name'.ljust(name_width)}  expected_findings  description")
    click.echo("-" * 80)
    for m in metas:
        click.echo(
            f"{m.name.ljust(name_width)}  "
            f"{str(m.expected_findings_count).rjust(17)}  "
            f"{m.description[:60]}"
        )


@fixtures.command("load")
@click.argument("name")
@click.pass_context
def fixtures_load_cmd(ctx: click.Context, name: str) -> None:
    settings = _settings(ctx)
    _ensure_paths(settings)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        result = fixtures_load_helper(name, conn)
    formatted = ", ".join(f"{k}={v}" for k, v in result.counts.items())
    click.echo(f"loaded fixture {name} ({result.tenant_id}): {formatted}")


@fixtures.command("load-all")
@click.pass_context
def fixtures_load_all_cmd(ctx: click.Context) -> None:
    settings = _settings(ctx)
    _ensure_paths(settings)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        for meta in fixtures_list_helper():
            result = fixtures_load_helper(meta.name, conn)
            formatted = ", ".join(f"{k}={v}" for k, v in result.counts.items())
            click.echo(f"loaded {meta.name}: {formatted}")


@fixtures.command("clear")
@click.argument("name")
@click.pass_context
def fixtures_clear_cmd(ctx: click.Context, name: str) -> None:
    settings = _settings(ctx)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        fixtures_clear_helper(name, conn)
    click.echo(f"cleared fixture {name}")


@fixtures.command("clear-all")
@click.pass_context
def fixtures_clear_all_cmd(ctx: click.Context) -> None:
    settings = _settings(ctx)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        fixtures_clear_all_helper(conn)
    click.echo("cleared all fixtures")


# --- audit subgroup ------------------------------------------------------


@cli.group()
def audit() -> None:
    """Run signalguard CA audit modules and inspect their findings."""


def _is_fixture_tenant(tenant: TenantConfig, settings: Settings) -> bool:
    return tenant.is_fixture


def _ensure_fixture_loaded(tenant: TenantConfig, conn: object) -> None:
    """Re-hydrate a fixture tenant before running an audit so the analyser
    sees fresh data even after the user cleared the DB by hand."""
    if tenant.is_fixture:
        fixtures_load_helper(tenant.display_name, conn)  # type: ignore[arg-type]


@audit.command("coverage")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def audit_coverage_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    from cstack_cli.audit_runner import (
        load_context,
        persist,
        run_coverage,
        severity_breakdown,
    )

    settings = _settings(ctx)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        _ensure_fixture_loaded(target, conn)
        context = load_context(conn, target)
        findings = run_coverage(context)
        persisted = persist(conn, findings)
    breakdown = severity_breakdown(findings)
    click.echo(
        f"{target.display_name}: coverage findings={len(findings)} new={persisted} {breakdown}"
    )


@audit.command("rules")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def audit_rules_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    from cstack_cli.audit_runner import (
        load_context,
        persist,
        run_rules,
        severity_breakdown,
    )

    settings = _settings(ctx)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        _ensure_fixture_loaded(target, conn)
        context = load_context(conn, target)
        findings = run_rules(context)
        persisted = persist(conn, findings)
    breakdown = severity_breakdown(findings)
    click.echo(f"{target.display_name}: rule findings={len(findings)} new={persisted} {breakdown}")


@audit.command("exclusions")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def audit_exclusions_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    from cstack_cli.audit_runner import (
        load_context,
        persist,
        run_exclusions,
        severity_breakdown,
    )

    settings = _settings(ctx)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        _ensure_fixture_loaded(target, conn)
        context = load_context(conn, target)
        findings = run_exclusions(context)
        persisted = persist(conn, findings)
    breakdown = severity_breakdown(findings)
    click.echo(
        f"{target.display_name}: exclusion findings={len(findings)} new={persisted} {breakdown}"
    )


@audit.command("all")
@click.option("--tenant", "tenant_identifier", required=True)
@click.pass_context
def audit_all_cmd(ctx: click.Context, tenant_identifier: str) -> None:
    from cstack_cli.audit_runner import (
        format_summary,
        load_context,
        persist,
        run_coverage,
        run_exclusions,
        run_rules,
        severity_breakdown,
    )

    settings = _settings(ctx)
    target = _resolve_tenant(ctx, tenant_identifier)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        _ensure_fixture_loaded(target, conn)
        context = load_context(conn, target)
        coverage = run_coverage(context)
        rules = run_rules(context)
        exclusions = run_exclusions(context)
        persist(conn, coverage)
        persist(conn, rules)
        persist(conn, exclusions)
    name = f"{target.display_name} (fixture)" if target.is_fixture else target.display_name
    summary = format_summary(
        name,
        {
            "coverage": severity_breakdown(coverage),
            "rules": severity_breakdown(rules),
            "exclusions": severity_breakdown(exclusions),
        },
    )
    click.echo(summary)


@audit.command("findings")
@click.option("--tenant", "tenant_identifier", required=True)
@click.option("--category", default=None, help="coverage | rule | exclusion")
@click.option("--min-severity", "min_severity", default=None)
@click.option("--rule-id", "rule_id", default=None)
@click.option("--json", "as_json", is_flag=True, default=False)
@click.pass_context
def audit_findings_cmd(
    ctx: click.Context,
    tenant_identifier: str,
    category: str | None,
    min_severity: str | None,
    rule_id: str | None,
    as_json: bool,
) -> None:
    from cstack_audit_core import latest_findings

    from cstack_cli.audit_runner import parse_severity

    settings = _settings(ctx)
    target = _resolve_tenant(ctx, tenant_identifier)
    severity = parse_severity(min_severity)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        rows = latest_findings(
            conn,
            tenant_id=target.tenant_id,
            category=category,
            min_severity=severity,
            rule_id=rule_id,
        )
    if as_json:
        import json as _json

        click.echo(_json.dumps([f.model_dump(mode="json") for f in rows], indent=2))
        return
    if not rows:
        click.echo(f"{target.display_name}: no findings match the filter")
        return
    sev_w = max(8, *(len(f.severity.value) for f in rows))
    rule_w = max(8, *(len(f.rule_id) for f in rows))
    click.echo(f"{'severity'.ljust(sev_w)}  {'rule'.ljust(rule_w)}  title")
    click.echo("-" * 80)
    for f in rows:
        click.echo(f"{f.severity.value.ljust(sev_w)}  {f.rule_id.ljust(rule_w)}  {f.title}")


@audit.command("list-rules")
def audit_list_rules_cmd() -> None:
    from cstack_audit_rules import RULE_REGISTRY

    if not RULE_REGISTRY:
        click.echo("(no rules registered)")
        return
    name_w = max(len("id"), *(len(r.metadata.id) for r in RULE_REGISTRY.values()))
    sev_w = max(len("severity"), *(len(r.metadata.severity.value) for r in RULE_REGISTRY.values()))
    click.echo(f"{'id'.ljust(name_w)}  {'severity'.ljust(sev_w)}  title")
    click.echo("-" * 80)
    for rule in sorted(RULE_REGISTRY.values(), key=lambda r: r.metadata.id):
        click.echo(
            f"{rule.metadata.id.ljust(name_w)}  "
            f"{rule.metadata.severity.value.ljust(sev_w)}  "
            f"{rule.metadata.title}"
        )


if __name__ == "__main__":
    cli()
