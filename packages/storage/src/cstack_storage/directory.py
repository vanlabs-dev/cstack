import json
from datetime import UTC, datetime

import duckdb
from cstack_schemas import DirectoryRole, Group, RoleAssignment, User


def upsert_users(conn: duckdb.DuckDBPyConnection, tenant_id: str, users: list[User]) -> int:
    if not users:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            tenant_id,
            u.id,
            u.display_name,
            u.user_principal_name,
            u.account_enabled,
            u.user_type,
            u.sign_in_activity.model_dump_json(by_alias=True, exclude_none=True)
            if u.sign_in_activity is not None
            else None,
            u.model_dump_json(by_alias=True, exclude_none=True),
            now,
        )
        for u in users
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO users
            (tenant_id, id, display_name, user_principal_name, account_enabled,
             user_type, sign_in_activity, raw, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def upsert_groups(conn: duckdb.DuckDBPyConnection, tenant_id: str, groups: list[Group]) -> int:
    if not groups:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            tenant_id,
            g.id,
            g.display_name,
            g.mail_enabled,
            g.security_enabled,
            json.dumps(g.members),
            g.model_dump_json(by_alias=True, exclude_none=True),
            now,
        )
        for g in groups
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO groups
            (tenant_id, id, display_name, mail_enabled, security_enabled,
             members, raw, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def upsert_directory_roles(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    roles: list[DirectoryRole],
) -> int:
    if not roles:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            tenant_id,
            r.id,
            r.display_name,
            r.description,
            r.role_template_id,
            json.dumps(r.members),
            r.model_dump_json(by_alias=True, exclude_none=True),
            now,
        )
        for r in roles
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO directory_roles
            (tenant_id, id, display_name, description, role_template_id,
             members, raw, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def upsert_role_assignments(
    conn: duckdb.DuckDBPyConnection,
    tenant_id: str,
    assignments: list[RoleAssignment],
) -> int:
    if not assignments:
        return 0
    now = datetime.now(UTC)
    rows = [
        (
            tenant_id,
            a.id,
            a.principal_id,
            a.role_definition_id,
            a.directory_scope_id,
            a.model_dump_json(by_alias=True, exclude_none=True),
            now,
        )
        for a in assignments
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO role_assignments
            (tenant_id, id, principal_id, role_definition_id, directory_scope_id,
             raw, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)
