from datetime import UTC, datetime

from cstack_audit_coverage import (
    UserSegment,
    is_service_account,
    resolve_segment_members,
)
from cstack_schemas import DirectoryRole, RoleAssignment, User

GLOBAL_ADMIN_TEMPLATE = "62e90394-69f5-4237-9190-012177145e10"
SECURITY_ADMIN_TEMPLATE = "194ae4cb-b126-40b2-bd5b-6091b380977d"
HELPDESK_TEMPLATE = "729827e3-9c14-49f7-bb1b-9608f156bbb8"


def _user(uid: str, **kwargs: object) -> User:
    payload: dict[str, object] = {"id": uid}
    payload.update(kwargs)
    return User.model_validate(payload)


def test_all_users_returns_every_id() -> None:
    users = [_user("u1"), _user("u2"), _user("u3")]
    members = resolve_segment_members(
        UserSegment.ALL_USERS, users, [], [], [], as_of=datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert members == {"u1", "u2", "u3"}


def test_guests_filters_user_type() -> None:
    users = [
        _user("u1", userType="Member"),
        _user("u2", userType="Guest"),
        _user("u3", userType="Guest"),
    ]
    members = resolve_segment_members(
        UserSegment.GUESTS, users, [], [], [], as_of=datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert members == {"u2", "u3"}


def test_service_accounts_via_name_pattern() -> None:
    now = datetime(2026, 4, 1, tzinfo=UTC)
    users = [
        _user("u1", displayName="svc_pipeline", userPrincipalName="svc_pipeline@x"),
        _user(
            "u2",
            displayName="Pat Example",
            userPrincipalName="pat@x",
            signInActivity={"lastSignInDateTime": "2026-03-30T10:00:00Z"},
        ),
        _user("u3", displayName="noreply-bot", userPrincipalName="noreply@x"),
    ]
    members = resolve_segment_members(UserSegment.SERVICE_ACCOUNTS, users, [], [], [], as_of=now)
    assert members == {"u1", "u3"}


def test_service_accounts_via_long_dormancy() -> None:
    now = datetime(2026, 4, 1, tzinfo=UTC)
    users = [
        _user(
            "u1",
            displayName="Pat",
            userPrincipalName="pat@x",
            signInActivity={"lastSignInDateTime": "2024-01-01T00:00:00Z"},
        ),
    ]
    assert is_service_account(users[0], now)


def test_admins_any_via_directory_role_members() -> None:
    roles = [
        DirectoryRole.model_validate(
            {
                "id": "role-1",
                "displayName": "Helpdesk Administrator",
                "roleTemplateId": HELPDESK_TEMPLATE,
                "members": ["u1", "u2"],
            }
        ),
        DirectoryRole.model_validate(
            {
                "id": "role-2",
                "displayName": "Cloud Application Administrator",
                "roleTemplateId": "158c047a-c907-4556-b7ef-446551a6b5f7",
                "members": ["u3"],
            }
        ),
    ]
    members = resolve_segment_members(
        UserSegment.ADMINS_ANY, [], [], roles, [], as_of=datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert members == {"u1", "u2", "u3"}


def test_privileged_roles_only_includes_tier_zero() -> None:
    roles = [
        DirectoryRole.model_validate(
            {
                "id": "role-1",
                "displayName": "Global Administrator",
                "roleTemplateId": GLOBAL_ADMIN_TEMPLATE,
                "members": ["u1"],
            }
        ),
        DirectoryRole.model_validate(
            {
                "id": "role-2",
                "displayName": "Helpdesk Administrator",
                "roleTemplateId": HELPDESK_TEMPLATE,
                "members": ["u2"],
            }
        ),
    ]
    members = resolve_segment_members(
        UserSegment.PRIVILEGED_ROLES, [], [], roles, [], as_of=datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert members == {"u1"}


def test_admins_any_supports_role_assignments() -> None:
    assignments = [
        RoleAssignment.model_validate(
            {"id": "a1", "principalId": "u1", "roleDefinitionId": SECURITY_ADMIN_TEMPLATE}
        )
    ]
    members = resolve_segment_members(
        UserSegment.ADMINS_ANY, [], [], [], assignments, as_of=datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert members == {"u1"}
