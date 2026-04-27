from datetime import UTC, datetime

from cstack_audit_coverage import (
    AppSegment,
    ProtectionLevel,
    UserSegment,
    compute_coverage,
)
from cstack_schemas import ConditionalAccessPolicy, DirectoryRole, User

GLOBAL_ADMIN_TEMPLATE = "62e90394-69f5-4237-9190-012177145e10"


def _policy(**fields: object) -> ConditionalAccessPolicy:
    base: dict[str, object] = {
        "id": fields.get("id", "p1"),
        "displayName": fields.get("displayName", "policy"),
        "state": fields.get("state", "enabled"),
        "conditions": fields.get(
            "conditions",
            {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "clientAppTypes": ["all"],
            },
        ),
        "grantControls": fields.get(
            "grantControls", {"operator": "OR", "builtInControls": ["mfa"]}
        ),
    }
    return ConditionalAccessPolicy.model_validate(base)


def test_mfa_all_users_all_apps_protects_everyone() -> None:
    users = [User.model_validate({"id": f"u{i}"}) for i in range(1, 4)]
    matrix = compute_coverage(
        tenant_id="t",
        policies=[_policy()],
        users=users,
        groups=[],
        roles=[],
        role_assignments=[],
        as_of=datetime(2026, 4, 1, tzinfo=UTC),
    )
    cell = next(
        c
        for c in matrix.cells
        if c.user_segment is UserSegment.ALL_USERS and c.app_segment is AppSegment.ALL_APPS
    )
    assert cell.protection_level == ProtectionLevel.MFA


def test_admin_exclusion_downgrades_admin_segment() -> None:
    # Policy targets all users but excludes the global admin user. Coverage
    # for the ADMINS_ANY segment should drop because the only admin is out.
    roles = [
        DirectoryRole.model_validate(
            {
                "id": "role-ga",
                "displayName": "Global Administrator",
                "roleTemplateId": GLOBAL_ADMIN_TEMPLATE,
                "members": ["admin-1"],
            }
        )
    ]
    users = [User.model_validate({"id": "admin-1"}), User.model_validate({"id": "user-1"})]
    pol = _policy(
        conditions={
            "users": {"includeUsers": ["All"], "excludeUsers": ["admin-1"]},
            "applications": {"includeApplications": ["All"]},
            "clientAppTypes": ["all"],
        }
    )
    matrix = compute_coverage(
        tenant_id="t",
        policies=[pol],
        users=users,
        groups=[],
        roles=roles,
        role_assignments=[],
        as_of=datetime(2026, 4, 1, tzinfo=UTC),
    )

    admin_cell = next(
        c
        for c in matrix.cells
        if c.user_segment is UserSegment.ADMINS_ANY and c.app_segment is AppSegment.ALL_APPS
    )
    all_cell = next(
        c
        for c in matrix.cells
        if c.user_segment is UserSegment.ALL_USERS and c.app_segment is AppSegment.ALL_APPS
    )
    assert admin_cell.protection_level == ProtectionLevel.NONE
    assert all_cell.protection_level == ProtectionLevel.MFA


def test_disabled_policy_does_not_contribute() -> None:
    pol = _policy(state="disabled")
    matrix = compute_coverage(
        tenant_id="t",
        policies=[pol],
        users=[User.model_validate({"id": "u1"})],
        groups=[],
        roles=[],
        role_assignments=[],
        as_of=datetime(2026, 4, 1, tzinfo=UTC),
    )
    cell = next(
        c
        for c in matrix.cells
        if c.user_segment is UserSegment.ALL_USERS and c.app_segment is AppSegment.ALL_APPS
    )
    assert cell.protection_level == ProtectionLevel.NONE


def test_report_only_policy_yields_report_only_level() -> None:
    pol = _policy(state="enabledForReportingButNotEnforced")
    matrix = compute_coverage(
        tenant_id="t",
        policies=[pol],
        users=[User.model_validate({"id": "u1"})],
        groups=[],
        roles=[],
        role_assignments=[],
        as_of=datetime(2026, 4, 1, tzinfo=UTC),
    )
    cell = next(
        c
        for c in matrix.cells
        if c.user_segment is UserSegment.ALL_USERS and c.app_segment is AppSegment.ALL_APPS
    )
    assert cell.protection_level == ProtectionLevel.REPORT_ONLY


def test_legacy_auth_recognised_via_client_app_types() -> None:
    pol = _policy(
        conditions={
            "users": {"includeUsers": ["All"]},
            "applications": {"includeApplications": ["All"]},
            "clientAppTypes": ["exchangeActiveSync", "other"],
        },
        grantControls={"operator": "OR", "builtInControls": ["block"]},
    )
    matrix = compute_coverage(
        tenant_id="t",
        policies=[pol],
        users=[User.model_validate({"id": "u1"})],
        groups=[],
        roles=[],
        role_assignments=[],
        as_of=datetime(2026, 4, 1, tzinfo=UTC),
    )
    cell = next(
        c
        for c in matrix.cells
        if c.user_segment is UserSegment.ALL_USERS and c.app_segment is AppSegment.LEGACY_AUTH
    )
    assert cell.protection_level == ProtectionLevel.MFA  # block treated as MFA-equivalent
