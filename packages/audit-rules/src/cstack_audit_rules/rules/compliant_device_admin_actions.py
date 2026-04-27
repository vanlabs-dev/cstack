from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import (
    PRIVILEGED_ROLE_TEMPLATE_IDS,
    has_built_in_control,
    is_enabled,
    targets_role_template_ids,
)
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.compliant-device-admin-actions",
    title="Admin actions require compliant device",
    severity=Severity.MEDIUM,
    description=(
        "Privileged role members should be required to use a compliant or "
        "Hybrid-Azure-AD-joined device for admin sign-ins, not just MFA."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/howto-conditional-access-policy-compliant-device",
        "https://www.cisa.gov/scuba",
    ],
    remediation_hint=(
        "Extend the admin CA policy to require compliantDevice OR "
        "domainJoinedDevice in addition to MFA."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p)
        and targets_role_template_ids(p, PRIVILEGED_ROLE_TEMPLATE_IDS)
        and (
            has_built_in_control(p, "compliantDevice")
            or has_built_in_control(p, "domainJoinedDevice")
        )
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
            summary=(
                "No enabled CA policy enforces compliantDevice or "
                "domainJoinedDevice on privileged admins."
            ),
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
