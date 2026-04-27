from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import (
    has_built_in_control,
    is_enabled,
    targets_all_users,
)
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.mfa-all-users",
    title="Require MFA for all users",
    severity=Severity.HIGH,
    description=(
        "Tenant should have at least one enabled CA policy that targets All "
        "users and requires MFA. Break-glass exclusions are expected and do "
        "not invalidate the rule."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-policy-common",
        "https://www.cisa.gov/scuba",
    ],
    remediation_hint=(
        "Create an enabled CA policy with includeUsers=All and "
        "grantControls.builtInControls includes 'mfa'."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p) and targets_all_users(p) and has_built_in_control(p, "mfa")
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
            summary="No enabled CA policy enforces MFA on All users.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
