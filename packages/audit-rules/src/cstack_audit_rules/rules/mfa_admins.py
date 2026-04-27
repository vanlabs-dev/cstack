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
    id="rule.mfa-admins",
    title="Require MFA for privileged admin roles",
    severity=Severity.CRITICAL,
    description=(
        "An MFA-on-all-users policy is not enough on its own; admins should "
        "have a dedicated policy targeting privileged role members so the "
        "control survives All-user policy changes."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/howto-conditional-access-policy-admin-mfa",
        "https://www.cisa.gov/scuba",
    ],
    remediation_hint=(
        "Add an enabled CA policy that includes the privileged role template "
        "ids and requires MFA (preferably AND compliantDevice)."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p)
        and targets_role_template_ids(p, PRIVILEGED_ROLE_TEMPLATE_IDS)
        and has_built_in_control(p, "mfa")
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
            summary="No enabled CA policy targets privileged role members with MFA.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
