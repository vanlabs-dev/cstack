from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import is_enabled
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.workload-identity-policies",
    title="Workload identity CA policies missing",
    severity=Severity.MEDIUM,
    description=(
        "Service principals running automation should be covered by at least "
        "one CA policy using clientApplications conditions, restricting where "
        "the workload identity can authenticate from."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/workload-identity",
    ],
    remediation_hint=(
        "Add an enabled CA policy with conditions.clientApplications listing "
        "the service principals that should be scoped, and a locations "
        "condition pinning egress IPs."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p)
        and p.conditions is not None
        and p.conditions.client_applications is not None
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
            summary="No enabled CA policy targets workload identities.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
