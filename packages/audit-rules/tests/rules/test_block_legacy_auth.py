from datetime import UTC, datetime

from cstack_audit_rules import AuditContext, run_rule
from cstack_schemas import ConditionalAccessPolicy


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


def test_fires_when_no_blocking_policy_exists() -> None:
    findings = run_rule("rule.block-legacy-auth", _ctx(policies=[]))
    assert len(findings) == 1


def test_does_not_fire_when_blocking_policy_present() -> None:
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p",
            "displayName": "Block legacy",
            "state": "enabled",
            "conditions": {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "clientAppTypes": ["other", "exchangeActiveSync"],
            },
            "grantControls": {"operator": "OR", "builtInControls": ["block"]},
        }
    )
    findings = run_rule("rule.block-legacy-auth", _ctx(policies=[policy]))
    assert findings == []
