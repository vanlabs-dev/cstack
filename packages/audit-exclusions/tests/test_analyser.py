from datetime import UTC, datetime, timedelta

from cstack_audit_exclusions import analyse_exclusions
from cstack_audit_rules import AuditContext
from cstack_schemas import (
    ConditionalAccessPolicy,
    DirectoryRole,
    Group,
    User,
)

GLOBAL_ADMIN_TEMPLATE = "62e90394-69f5-4237-9190-012177145e10"


def _ctx(
    policies: list[ConditionalAccessPolicy],
    users: list[User],
    groups: list[Group] | None = None,
    roles: list[DirectoryRole] | None = None,
) -> AuditContext:
    return AuditContext(
        tenant_id="t",
        policies=policies,
        users=users,
        groups=groups or [],
        roles=roles or [],
        role_assignments=[],
        named_locations=[],
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )


def test_stale_user_exclusion_fires() -> None:
    user = User.model_validate(
        {
            "id": "u1",
            "displayName": "Pat",
            "accountEnabled": True,
            "signInActivity": {"lastSignInDateTime": "2025-01-01T00:00:00Z"},
        }
    )
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p1",
            "displayName": "MFA all (with exception)",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": ["u1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([policy], [user]))
    rule_ids = [f.rule_id for f in findings]
    assert "exclusion.stale-user" in rule_ids


def test_orphan_exclusion_fires_for_disabled_account() -> None:
    user = User.model_validate(
        {
            "id": "u1",
            "displayName": "Old User",
            "accountEnabled": False,
            "signInActivity": {"lastSignInDateTime": "2026-04-15T00:00:00Z"},
        }
    )
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p1",
            "displayName": "MFA exception",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": ["u1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([policy], [user]))
    assert any(f.rule_id == "exclusion.orphan-user" for f in findings)


def test_admin_mfa_bypass_fires_with_no_alternate() -> None:
    admin = User.model_validate(
        {
            "id": "admin-1",
            "displayName": "Admin",
            "accountEnabled": True,
            "signInActivity": {
                "lastSignInDateTime": (datetime(2026, 4, 25, tzinfo=UTC)).isoformat()
            },
        }
    )
    role = DirectoryRole.model_validate(
        {
            "id": "role-ga",
            "displayName": "Global Administrator",
            "roleTemplateId": GLOBAL_ADMIN_TEMPLATE,
            "members": ["admin-1"],
        }
    )
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p1",
            "displayName": "Admin MFA exception",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": ["admin-1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([policy], [admin], roles=[role]))
    assert any(f.rule_id == "exclusion.admin-mfa-bypass" for f in findings)


def test_admin_mfa_bypass_does_not_fire_when_alternate_exists() -> None:
    admin = User.model_validate(
        {
            "id": "admin-1",
            "displayName": "Admin",
            "accountEnabled": True,
            "signInActivity": {
                "lastSignInDateTime": (datetime(2026, 4, 25, tzinfo=UTC)).isoformat()
            },
        }
    )
    role = DirectoryRole.model_validate(
        {
            "id": "role-ga",
            "displayName": "Global Administrator",
            "roleTemplateId": GLOBAL_ADMIN_TEMPLATE,
            "members": ["admin-1"],
        }
    )
    excluding = ConditionalAccessPolicy.model_validate(
        {
            "id": "p1",
            "displayName": "Admin exception",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": ["admin-1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    alternate = ConditionalAccessPolicy.model_validate(
        {
            "id": "p2",
            "displayName": "All-user MFA fallback",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([excluding, alternate], [admin], roles=[role]))
    assert not any(f.rule_id == "exclusion.admin-mfa-bypass" for f in findings)


def test_creep_fires_above_threshold() -> None:
    excluded_ids = [f"u{i}" for i in range(6)]
    users = [
        User.model_validate(
            {
                "id": uid,
                "accountEnabled": True,
                "signInActivity": {
                    "lastSignInDateTime": (
                        datetime(2026, 4, 27, tzinfo=UTC) - timedelta(days=1)
                    ).isoformat()
                },
            }
        )
        for uid in excluded_ids
    ]
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p-creep",
            "displayName": "Many exceptions",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": excluded_ids},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([policy], users))
    assert any(f.rule_id == "exclusion.creep" for f in findings)


def test_undocumented_fires_when_no_keyword_in_name() -> None:
    user = User.model_validate(
        {
            "id": "u1",
            "displayName": "Pat",
            "accountEnabled": True,
            "signInActivity": {"lastSignInDateTime": "2026-04-25T00:00:00Z"},
        }
    )
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p-undoc",
            "displayName": "Some random policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": ["u1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([policy], [user]))
    assert any(f.rule_id == "exclusion.undocumented" for f in findings)


def test_undocumented_does_not_fire_when_name_contains_keyword() -> None:
    user = User.model_validate(
        {
            "id": "u1",
            "displayName": "Pat",
            "accountEnabled": True,
            "signInActivity": {"lastSignInDateTime": "2026-04-25T00:00:00Z"},
        }
    )
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p-doc",
            "displayName": "Break-glass exception policy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"], "excludeUsers": ["u1"]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = analyse_exclusions(_ctx([policy], [user]))
    assert not any(f.rule_id == "exclusion.undocumented" for f in findings)
