from datetime import UTC, datetime

from cstack_audit_rules import AuditContext, run_rule
from cstack_schemas import ConditionalAccessPolicy


def _ctx(policies: list[ConditionalAccessPolicy], as_of: datetime) -> AuditContext:
    return AuditContext(
        tenant_id="t",
        policies=policies,
        users=[],
        groups=[],
        roles=[],
        role_assignments=[],
        named_locations=[],
        as_of=as_of,
    )


def test_fires_for_old_disabled_policy() -> None:
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p",
            "displayName": "Old disabled",
            "state": "disabled",
            "modifiedDateTime": "2024-01-01T00:00:00Z",
        }
    )
    findings = run_rule(
        "rule.disabled-policies-old",
        _ctx(policies=[policy], as_of=datetime(2026, 4, 28, tzinfo=UTC)),
    )
    assert len(findings) == 1
    assert findings[0].affected_objects[0].id == "p"


def test_does_not_fire_for_recent_disabled_policy() -> None:
    policy = ConditionalAccessPolicy.model_validate(
        {
            "id": "p",
            "displayName": "Recent disabled",
            "state": "disabled",
            "modifiedDateTime": "2026-04-01T00:00:00Z",
        }
    )
    findings = run_rule(
        "rule.disabled-policies-old",
        _ctx(policies=[policy], as_of=datetime(2026, 4, 28, tzinfo=UTC)),
    )
    assert findings == []
