import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import duckdb
from cstack_schemas import (
    ConditionalAccessPolicy,
    CountryNamedLocation,
    DirectoryRole,
    Group,
    IpNamedLocation,
    NamedLocationAdapter,
    RoleAssignment,
    User,
)
from cstack_storage import get_policies

NamedLocationVariant = IpNamedLocation | CountryNamedLocation


@dataclass(frozen=True)
class AuditContext:
    """All inputs an audit rule may need. Immutable so rules cannot mutate
    shared state between evaluations."""

    tenant_id: str
    policies: list[ConditionalAccessPolicy]
    users: list[User]
    groups: list[Group]
    roles: list[DirectoryRole]
    role_assignments: list[RoleAssignment]
    named_locations: list[NamedLocationVariant]
    as_of: datetime
    extra: dict[str, Any] = field(default_factory=dict)


def load_context_from_db(
    conn: duckdb.DuckDBPyConnection, tenant_id: str, as_of: datetime
) -> AuditContext:
    """Hydrate an AuditContext from the cstack DuckDB store."""
    policies = get_policies(conn, tenant_id)

    user_rows = conn.execute("SELECT raw FROM users WHERE tenant_id = ?", [tenant_id]).fetchall()
    users = [User.model_validate(json.loads(r[0])) for r in user_rows]

    group_rows = conn.execute("SELECT raw FROM groups WHERE tenant_id = ?", [tenant_id]).fetchall()
    groups = [Group.model_validate(json.loads(r[0])) for r in group_rows]

    role_rows = conn.execute(
        "SELECT raw FROM directory_roles WHERE tenant_id = ?", [tenant_id]
    ).fetchall()
    roles = [DirectoryRole.model_validate(json.loads(r[0])) for r in role_rows]

    assignment_rows = conn.execute(
        "SELECT raw FROM role_assignments WHERE tenant_id = ?", [tenant_id]
    ).fetchall()
    role_assignments = [RoleAssignment.model_validate(json.loads(r[0])) for r in assignment_rows]

    location_rows = conn.execute(
        """
        SELECT id, display_name, location_type, ip_ranges, countries, is_trusted
        FROM named_locations WHERE tenant_id = ?
        """,
        [tenant_id],
    ).fetchall()
    named_locations: list[NamedLocationVariant] = []
    for row in location_rows:
        if row[2] == "ip":
            payload: dict[str, Any] = {
                "@odata.type": "#microsoft.graph.ipNamedLocation",
                "id": row[0],
                "displayName": row[1],
                "isTrusted": row[5],
                "ipRanges": json.loads(row[3]) if row[3] else [],
            }
        else:
            payload = {
                "@odata.type": "#microsoft.graph.countryNamedLocation",
                "id": row[0],
                "displayName": row[1],
                "countriesAndRegions": json.loads(row[4]) if row[4] else [],
            }
        named_locations.append(NamedLocationAdapter.validate_python(payload))

    return AuditContext(
        tenant_id=tenant_id,
        policies=policies,
        users=users,
        groups=groups,
        roles=roles,
        role_assignments=role_assignments,
        named_locations=named_locations,
        as_of=as_of,
    )
