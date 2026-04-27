from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import (
    has_built_in_control,
    includes_legacy_client_app_types,
    is_enabled,
)
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.block-legacy-auth",
    title="Block legacy authentication",
    severity=Severity.HIGH,
    description=(
        "Tenant should have at least one enabled CA policy that blocks legacy "
        "auth client app types (exchangeActiveSync, other) for all interactive "
        "users."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/howto-conditional-access-policy-block-legacy",
        "https://www.cisa.gov/scuba",
        "https://www.cisecurity.org/benchmark/microsoft_365",
    ],
    remediation_hint=(
        "Add an enabled CA policy with clientAppTypes [other, exchangeActiveSync] "
        "and grantControls.builtInControls = [block]."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    blocking = [
        p
        for p in context.policies
        if is_enabled(p)
        and includes_legacy_client_app_types(p)
        and has_built_in_control(p, "block")
    ]
    if blocking:
        return []
    return [
        make_finding(
            METADATA,
            tenant_id=context.tenant_id,
            affected_objects=[
                AffectedObject(type="tenant", id=context.tenant_id, display_name="tenant")
            ],
            summary="No enabled CA policy blocks legacy authentication.",
            evidence={"policies_targeting_legacy_auth": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
