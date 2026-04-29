import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from cstack_schemas import (
    ConditionalAccessPolicy,
    DirectoryRole,
    Group,
    NamedLocationAdapter,
    TenantConfig,
    User,
)
from cstack_storage import (
    register_tenant,
    remove_tenant_db,
    upsert_ca_policies,
    upsert_directory_roles,
    upsert_groups,
    upsert_named_locations,
    upsert_users,
    write_raw,
)
from pydantic import BaseModel, ConfigDict

from cstack_fixtures.registry import (
    FIXTURE_CERT_THUMBPRINT,
    FIXTURE_CLIENT_ID,
)


class FixtureExpectedFindings(BaseModel):
    """Calibrated expected findings, populated by the Sprint 2 audit run.

    These counts are the new ground truth that integration tests assert
    against. Re-calibrate by re-running ``cstack audit all`` against each
    fixture and updating metadata.json.
    """

    model_config = ConfigDict(populate_by_name=True)

    total: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_rule_id: dict[str, int]


class FixtureSigninScenario(BaseModel):
    """Per-scenario sign-in corpus location and ground-truth pointer."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    signins_path: str
    ground_truth_path: str


class FixtureMetadata(BaseModel):
    """Header for a fixture tenant. Mirrors metadata.json on disk."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    tenant_id: str
    expected_findings: FixtureExpectedFindings
    scenario_tags: list[str]
    calibrated_at: str | None = None
    notes: str | None = None
    signin_scenarios: list[FixtureSigninScenario] = []
    anomaly_calibration: dict[str, Any] | None = None


class SigninLoadResult(BaseModel):
    """Counts returned by load_signins."""

    tenant_id: str
    scenario: str
    rows_written: int
    ground_truth_count: int


class FixtureLoadResult(BaseModel):
    """Counts of records hydrated per resource type for a single load call."""

    tenant_id: str
    name: str
    counts: dict[str, int]


_DATA_DIR = Path(__file__).parent / "data"

# Resource types mapped to (json filename, raw resource label) pairs. Order
# matters: tenants must be registered before any data rows reference them.
_RESOURCE_FILES: tuple[tuple[str, str], ...] = (
    ("ca-policies.json", "ca-policies"),
    ("named-locations.json", "named-locations"),
    ("users.json", "users"),
    ("groups.json", "groups"),
    ("directory-roles.json", "directory-roles"),
)


def list_fixtures() -> list[FixtureMetadata]:
    """Return metadata for every fixture bundled with the package."""
    fixtures: list[FixtureMetadata] = []
    if not _DATA_DIR.exists():
        return fixtures
    for tenant_dir in sorted(_DATA_DIR.iterdir()):
        meta_path = tenant_dir / "metadata.json"
        if not tenant_dir.is_dir() or not meta_path.exists():
            continue
        fixtures.append(FixtureMetadata.model_validate_json(meta_path.read_text(encoding="utf-8")))
    return fixtures


def load_fixture(name: str, conn: duckdb.DuckDBPyConnection) -> FixtureLoadResult:
    """Hydrate a single fixture tenant into the database.

    Writes raw payloads to ``raw_ingestions`` and parses each into the
    normalised tables, mirroring what a live extract would produce. Idempotent
    by virtue of the upsert helpers in :mod:`cstack_storage`.
    """
    tenant_dir = _DATA_DIR / name
    if not tenant_dir.exists():
        raise FileNotFoundError(f"fixture {name!r} not found at {tenant_dir}")

    meta = FixtureMetadata.model_validate_json(
        (tenant_dir / "metadata.json").read_text(encoding="utf-8")
    )

    tenant = TenantConfig(
        tenant_id=meta.tenant_id,
        display_name=name,
        client_id=FIXTURE_CLIENT_ID,
        cert_thumbprint=FIXTURE_CERT_THUMBPRINT,
        cert_subject=f"CN=cstack-fixture-{name}",
        added_at=datetime.now(UTC),
        is_fixture=True,
    )
    register_tenant(conn, tenant)

    counts: dict[str, int] = {}

    counts["ca_policies"] = _load_ca_policies(conn, meta.tenant_id, tenant_dir)
    counts["named_locations"] = _load_named_locations(conn, meta.tenant_id, tenant_dir)
    counts["users"] = _load_users(conn, meta.tenant_id, tenant_dir)
    counts["groups"] = _load_groups(conn, meta.tenant_id, tenant_dir)
    counts["directory_roles"] = _load_directory_roles(conn, meta.tenant_id, tenant_dir)

    return FixtureLoadResult(tenant_id=meta.tenant_id, name=name, counts=counts)


def clear_fixture(name: str, conn: duckdb.DuckDBPyConnection) -> None:
    """Remove all rows belonging to the named fixture tenant."""
    meta = FixtureMetadata.model_validate_json(
        (_DATA_DIR / name / "metadata.json").read_text(encoding="utf-8")
    )
    remove_tenant_db(conn, meta.tenant_id)


def load_signins(name: str, scenario: str, conn: duckdb.DuckDBPyConnection) -> SigninLoadResult:
    """Hydrate sign-ins for a fixture tenant and named scenario into DuckDB."""
    from cstack_schemas import SignIn
    from cstack_storage import upsert_signins

    tenant_dir = _DATA_DIR / name
    meta = FixtureMetadata.model_validate_json(
        (tenant_dir / "metadata.json").read_text(encoding="utf-8")
    )
    scenario_dir = tenant_dir / "signins" / scenario
    payload = json.loads((scenario_dir / "signins.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{scenario_dir}: signins.json must be a JSON array")
    parsed = [SignIn.model_validate(item) for item in payload if isinstance(item, dict)]
    rows = upsert_signins(conn, meta.tenant_id, parsed)
    ground_truth = json.loads((scenario_dir / "ground_truth.json").read_text(encoding="utf-8"))
    return SigninLoadResult(
        tenant_id=meta.tenant_id,
        scenario=scenario,
        rows_written=rows,
        ground_truth_count=len(ground_truth) if isinstance(ground_truth, list) else 0,
    )


def clear_signins(name: str, scenario: str, conn: duckdb.DuckDBPyConnection) -> None:
    """Remove sign-ins matching the scenario's ids. ``scenario`` here is purely
    informative: rows are scoped by tenant_id, but the caller passes the name
    so it can clear before reloading a different scenario."""
    meta = FixtureMetadata.model_validate_json(
        (_DATA_DIR / name / "metadata.json").read_text(encoding="utf-8")
    )
    conn.execute("DELETE FROM signins WHERE tenant_id = ?", [meta.tenant_id])
    _ = scenario  # currently unused; reserved for per-scenario partitioning later


def ground_truth_for(name: str, scenario: str) -> list[dict[str, Any]]:
    """Read the ground-truth label list for a fixture/scenario pair."""
    path = _DATA_DIR / name / "signins" / scenario / "ground_truth.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def clear_all_fixtures(conn: duckdb.DuckDBPyConnection) -> None:
    """Remove every fixture tenant from the DB. Useful for clean-slate tests."""
    for fixture in list_fixtures():
        clear_fixture(fixture.name, conn)


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON array, got {type(payload).__name__}")
    return [item for item in payload if isinstance(item, dict)]


def _load_ca_policies(conn: duckdb.DuckDBPyConnection, tenant_id: str, tenant_dir: Path) -> int:
    path = tenant_dir / "ca-policies.json"
    payload = _read_json_array(path)
    write_raw(conn, tenant_id, "ca-policies", payload, source_path=str(path))
    parsed = [ConditionalAccessPolicy.model_validate(item) for item in payload]
    return upsert_ca_policies(conn, tenant_id, parsed)


def _load_named_locations(conn: duckdb.DuckDBPyConnection, tenant_id: str, tenant_dir: Path) -> int:
    path = tenant_dir / "named-locations.json"
    payload = _read_json_array(path)
    write_raw(conn, tenant_id, "named-locations", payload, source_path=str(path))
    parsed = [NamedLocationAdapter.validate_python(item) for item in payload]
    return upsert_named_locations(conn, tenant_id, parsed)


def _load_users(conn: duckdb.DuckDBPyConnection, tenant_id: str, tenant_dir: Path) -> int:
    path = tenant_dir / "users.json"
    payload = _read_json_array(path)
    write_raw(conn, tenant_id, "users", payload, source_path=str(path))
    parsed = [User.model_validate(item) for item in payload]
    return upsert_users(conn, tenant_id, parsed)


def _load_groups(conn: duckdb.DuckDBPyConnection, tenant_id: str, tenant_dir: Path) -> int:
    path = tenant_dir / "groups.json"
    payload = _read_json_array(path)
    write_raw(conn, tenant_id, "groups", payload, source_path=str(path))
    parsed = [Group.model_validate(item) for item in payload]
    return upsert_groups(conn, tenant_id, parsed)


def _load_directory_roles(conn: duckdb.DuckDBPyConnection, tenant_id: str, tenant_dir: Path) -> int:
    path = tenant_dir / "directory-roles.json"
    payload = _read_json_array(path)
    write_raw(conn, tenant_id, "directory-roles", payload, source_path=str(path))
    parsed = [DirectoryRole.model_validate(item) for item in payload]
    return upsert_directory_roles(conn, tenant_id, parsed)
