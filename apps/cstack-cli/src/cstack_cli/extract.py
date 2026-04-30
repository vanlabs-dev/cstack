"""Extract orchestration. Routes between live Graph fetches and the bundled
fixture corpus depending on whether the target tenant is marked is_fixture.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from cstack_fixtures import load_fixture
from cstack_graph_client import (
    build_client,
    fetch_all_ca_policies,
    fetch_all_directory_roles,
    fetch_all_groups,
    fetch_all_named_locations,
    fetch_all_users,
    load_certificate_credential_for_tenant,
)
from cstack_schemas import (
    ConditionalAccessPolicy,
    DirectoryRole,
    Group,
    NamedLocationAdapter,
    TenantConfig,
    User,
)
from cstack_storage import (
    upsert_ca_policies,
    upsert_directory_roles,
    upsert_groups,
    upsert_named_locations,
    upsert_users,
    write_raw,
)

LOG = logging.getLogger(__name__)

# Resource name -> normalised filename written under data/raw/<tenant>/<date>/.
RESOURCE_FILES: dict[str, str] = {
    "ca-policies": "ca-policies.json",
    "named-locations": "named-locations.json",
    "users": "users.json",
    "groups": "groups.json",
    "directory-roles": "directory-roles.json",
}


def write_raw_file(
    data_dir: Path, tenant_id: str, resource: str, payload: list[dict[str, Any]]
) -> Path:
    """Persist a raw extract to ``data/raw/<tenant>/<yyyy-mm-dd>/<resource>.json``."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_dir = data_dir / "raw" / tenant_id / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / RESOURCE_FILES[resource]
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def _fixture_payload(name: str, resource: str) -> list[dict[str, Any]]:
    """Read a fixture resource directly from the bundled corpus."""
    from cstack_fixtures.loader import _DATA_DIR  # private but stable for fixtures

    file_path = _DATA_DIR / name / RESOURCE_FILES[resource]
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{file_path}: expected a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def extract_ca_policies(
    conn: duckdb.DuckDBPyConnection,
    tenant: TenantConfig,
    data_dir: Path,
) -> int:
    """Pull CA policies for one tenant. Returns rows upserted."""
    payload = _resolve_payload(conn, tenant, "ca-policies")
    out_path = write_raw_file(data_dir, tenant.tenant_id, "ca-policies", payload)
    write_raw(conn, tenant.tenant_id, "ca-policies", payload, source_path=str(out_path))
    parsed = [ConditionalAccessPolicy.model_validate(item) for item in payload]
    written = upsert_ca_policies(conn, tenant.tenant_id, parsed)
    LOG.info(
        "extract_ca_policies",
        extra={"tenant_id": tenant.tenant_id, "rows": written, "path": str(out_path)},
    )
    return written


def extract_named_locations(
    conn: duckdb.DuckDBPyConnection,
    tenant: TenantConfig,
    data_dir: Path,
) -> int:
    payload = _resolve_payload(conn, tenant, "named-locations")
    out_path = write_raw_file(data_dir, tenant.tenant_id, "named-locations", payload)
    write_raw(conn, tenant.tenant_id, "named-locations", payload, source_path=str(out_path))
    parsed = [NamedLocationAdapter.validate_python(item) for item in payload]
    return upsert_named_locations(conn, tenant.tenant_id, parsed)


def extract_directory(
    conn: duckdb.DuckDBPyConnection,
    tenant: TenantConfig,
    data_dir: Path,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    users_payload = _resolve_payload(conn, tenant, "users")
    out_users = write_raw_file(data_dir, tenant.tenant_id, "users", users_payload)
    write_raw(conn, tenant.tenant_id, "users", users_payload, source_path=str(out_users))
    counts["users"] = upsert_users(
        conn, tenant.tenant_id, [User.model_validate(u) for u in users_payload]
    )

    groups_payload = _resolve_payload(conn, tenant, "groups")
    out_groups = write_raw_file(data_dir, tenant.tenant_id, "groups", groups_payload)
    write_raw(conn, tenant.tenant_id, "groups", groups_payload, source_path=str(out_groups))
    counts["groups"] = upsert_groups(
        conn, tenant.tenant_id, [Group.model_validate(g) for g in groups_payload]
    )

    roles_payload = _resolve_payload(conn, tenant, "directory-roles")
    out_roles = write_raw_file(data_dir, tenant.tenant_id, "directory-roles", roles_payload)
    write_raw(conn, tenant.tenant_id, "directory-roles", roles_payload, source_path=str(out_roles))
    counts["directory_roles"] = upsert_directory_roles(
        conn, tenant.tenant_id, [DirectoryRole.model_validate(r) for r in roles_payload]
    )

    return counts


def _resolve_payload(
    conn: duckdb.DuckDBPyConnection, tenant: TenantConfig, resource: str
) -> list[dict[str, Any]]:
    """Decide whether to read from the fixture corpus or call Graph."""
    if tenant.is_fixture:
        # Ensure the fixture is hydrated in the DB before extract starts. This
        # is a no-op the second time because the loader is idempotent.
        load_fixture(tenant.display_name, conn)
        return _fixture_payload(tenant.display_name, resource)
    return asyncio.run(_fetch_live(tenant, resource))


async def _fetch_live(tenant: TenantConfig, resource: str) -> list[dict[str, Any]]:
    """Pull a single resource from Microsoft Graph."""
    credential = load_certificate_credential_for_tenant(tenant)
    client = build_client(credential)
    if resource == "ca-policies":
        return await fetch_all_ca_policies(client)
    if resource == "named-locations":
        return await fetch_all_named_locations(client)
    if resource == "users":
        return await fetch_all_users(client)
    if resource == "groups":
        return await fetch_all_groups(client)
    if resource == "directory-roles":
        return await fetch_all_directory_roles(client)
    raise ValueError(f"unknown resource type: {resource!r}")
