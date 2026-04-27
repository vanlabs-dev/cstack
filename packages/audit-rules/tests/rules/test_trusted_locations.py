from datetime import UTC, datetime

from cstack_audit_rules import AuditContext, run_rule
from cstack_audit_rules.context import NamedLocationVariant
from cstack_schemas import IpNamedLocation


def _ctx(locations: list[NamedLocationVariant]) -> AuditContext:
    return AuditContext(
        tenant_id="t",
        policies=[],
        users=[],
        groups=[],
        roles=[],
        role_assignments=[],
        named_locations=locations,
        as_of=datetime(2026, 4, 28, tzinfo=UTC),
    )


def test_fires_when_no_trusted_locations() -> None:
    findings = run_rule("rule.trusted-locations-defined", _ctx(locations=[]))
    assert len(findings) == 1


def test_does_not_fire_when_trusted_ip_location_present() -> None:
    loc = IpNamedLocation.model_validate(
        {
            "@odata.type": "#microsoft.graph.ipNamedLocation",
            "id": "loc-1",
            "displayName": "office",
            "isTrusted": True,
            "ipRanges": [
                {"@odata.type": "#microsoft.graph.iPv4CidrRange", "cidrAddress": "10.0.0.0/8"}
            ],
        }
    )
    findings = run_rule("rule.trusted-locations-defined", _ctx(locations=[loc]))
    assert findings == []
