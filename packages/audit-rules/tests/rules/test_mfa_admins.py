from datetime import UTC, datetime

from cstack_audit_rules import AuditContext, run_rule
from cstack_schemas import ConditionalAccessPolicy

GLOBAL_ADMIN_TEMPLATE = "62e90394-69f5-4237-9190-012177145e10"


def _ctx(policies: list[ConditionalAccessPolicy]) -> AuditContext:
    return AuditContext(
        tenant_id="t",
        policies=policies,
        users=[],
        groups=[],
        roles=[],
        role_assignments=[],
        named_locations=[],
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )


def test_fires_when_no_admin_mfa_policy() -> None:
    findings = run_rule("rule.mfa-admins", _ctx(policies=[]))
    assert len(findings) == 1


def test_does_not_fire_when_admin_mfa_present() -> None:
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p",
            "displayName": "Admin MFA",
            "state": "enabled",
            "conditions": {
                "users": {"includeRoles": [GLOBAL_ADMIN_TEMPLATE]},
                "applications": {"includeApplications": ["All"]},
            },
            "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
        }
    )
    findings = run_rule("rule.mfa-admins", _ctx(policies=[policy]))
    assert findings == []
