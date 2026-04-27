from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import (
    SENSITIVE_APP_IDS,
    has_built_in_control,
    is_enabled,
    targets_app_id,
)
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.device-compliance-sensitive-apps",
    title="Sensitive apps require compliant device",
    severity=Severity.MEDIUM,
    description=(
        "Apps holding the most sensitive data (Azure Portal, Graph PowerShell, "
        "SharePoint/OneDrive) should require a compliant device for access."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/howto-conditional-access-policy-compliant-device",
    ],
    remediation_hint=(
        "Add an enabled CA policy targeting the sensitive app ids with "
        "grantControls.builtInControls including compliantDevice."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p)
        and targets_app_id(p, SENSITIVE_APP_IDS)
        and has_built_in_control(p, "compliantDevice")
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
            summary="No enabled CA policy enforces compliantDevice on sensitive apps.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
