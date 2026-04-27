from cstack_schemas import DirectoryRole, Group, RoleAssignment, SignInActivity, User


def test_user_with_signin_activity() -> None:
    payload: dict[str, object] = {
        "id": "user-1",
        "displayName": "Pat Example",
        "userPrincipalName": "pat@example.com",
        "accountEnabled": True,
        "userType": "Member",
        "signInActivity": {
            "lastSignInDateTime": "2026-01-15T08:30:00Z",
        },
    }
    user = User.model_validate(payload)
    assert user.user_principal_name == "pat@example.com"
    assert isinstance(user.sign_in_activity, SignInActivity)
    assert user.sign_in_activity.last_sign_in_date_time is not None


def test_user_without_signin_activity() -> None:
    user = User.model_validate({"id": "user-2"})
    assert user.sign_in_activity is None


def test_group_minimum() -> None:
    group = Group.model_validate({"id": "group-1", "displayName": "engineering"})
    assert group.display_name == "engineering"
    assert group.members == []


def test_directory_role_minimum() -> None:
    role = DirectoryRole.model_validate({"id": "role-1", "displayName": "Global Administrator"})
    assert role.display_name == "Global Administrator"


def test_role_assignment_minimum() -> None:
    assignment = RoleAssignment.model_validate(
        {
            "id": "assign-1",
            "principalId": "user-1",
            "roleDefinitionId": "62e90394-69f5-4237-9190-012177145e10",
            "directoryScopeId": "/",
        }
    )
    assert assignment.principal_id == "user-1"
    assert assignment.directory_scope_id == "/"
