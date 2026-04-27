from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import is_enabled
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.risk-based-user",
    title="User risk policy missing",
    severity=Severity.HIGH,
    description=(
        "Tenant should have an enabled CA policy that triggers on "
        "userRiskLevels (high) so compromised accounts are forced through "
        "secure password reset."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/identity-protection/howto-identity-protection-configure-risk-policies",
    ],
    remediation_hint=(
        "Add an enabled CA policy with userRiskLevels including high and "
        "grantControls.builtInControls including passwordChange."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p)
        and p.conditions is not None
        and p.conditions.user_risk_levels
        and "high" in p.conditions.user_risk_levels
    ]
    if qualifying:
        return []
    return [
        make_finding(
            METADATA,
            tenant_id=context.tenant_id,
            affected_objects=[
                AffectedObject(type="tenant", id=context.tenant_id, display_name="tenant")
            ],
            summary="No enabled CA policy uses userRiskLevels.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
