import duckdb
from cstack_schemas import DirectoryRole, Group, RoleAssignment, User
from cstack_storage import (
    upsert_directory_roles,
    upsert_groups,
    upsert_role_assignments,
    upsert_users,
)

TENANT = "00000000-0000-0000-0000-0000000000cc"


def test_upsert_users(db: duckdb.DuckDBPyConnection) -> None:
    users = [
        User.model_validate({"id": "u1", "displayName": "Pat", "userPrincipalName": "p@x"}),
        User.model_validate({"id": "u2", "displayName": "Sam"}),
    ]
    written = upsert_users(db, TENANT, users)
    assert written == 2
    rows = db.execute("SELECT id, display_name FROM users WHERE tenant_id = ?", [TENANT]).fetchall()
    assert {(r[0], r[1]) for r in rows} == {("u1", "Pat"), ("u2", "Sam")}


def test_upsert_users_idempotent(db: duckdb.DuckDBPyConnection) -> None:
    user = User.model_validate({"id": "u1", "displayName": "v1"})
    upsert_users(db, TENANT, [user])
    user_v2 = User.model_validate({"id": "u1", "displayName": "v2"})
    upsert_users(db, TENANT, [user_v2])
    rows = db.execute("SELECT display_name FROM users WHERE tenant_id = ?", [TENANT]).fetchall()
    assert rows == [("v2",)]


def test_upsert_groups(db: duckdb.DuckDBPyConnection) -> None:
    groups = [Group.model_validate({"id": "g1", "displayName": "Engineering"})]
    assert upsert_groups(db, TENANT, groups) == 1


def test_upsert_directory_roles(db: duckdb.DuckDBPyConnection) -> None:
    roles = [DirectoryRole.model_validate({"id": "r1", "displayName": "Global Admin"})]
    assert upsert_directory_roles(db, TENANT, roles) == 1


def test_upsert_role_assignments(db: duckdb.DuckDBPyConnection) -> None:
    assignments = [
        RoleAssignment.model_validate({"id": "a1", "principalId": "u1", "roleDefinitionId": "rd1"})
    ]
    assert upsert_role_assignments(db, TENANT, assignments) == 1
