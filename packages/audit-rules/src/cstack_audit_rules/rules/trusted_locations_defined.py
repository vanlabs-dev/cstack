from cstack_audit_core import AffectedObject, Finding, Severity
from cstack_schemas import IpNamedLocation

from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.trusted-locations-defined",
    title="Trusted IP named locations defined",
    severity=Severity.LOW,
    description=(
        "Tenant should have at least one trusted IP named location so location "
        "based CA conditions can downgrade interactive challenges in the office."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/location-condition",
    ],
    remediation_hint=(
        "Define a trusted IP named location for the corporate egress range "
        "and reference it from CA policy locations conditions where appropriate."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    trusted = [
        loc
        for loc in context.named_locations
        if isinstance(loc, IpNamedLocation) and loc.is_trusted
    ]
    if trusted:
        return []
    return [
        make_finding(
            METADATA,
            tenant_id=context.tenant_id,
            affected_objects=[
                AffectedObject(type="tenant", id=context.tenant_id, display_name="tenant")
            ],
            summary="Tenant has no trusted IP named locations.",
            evidence={"trusted_ip_locations": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
