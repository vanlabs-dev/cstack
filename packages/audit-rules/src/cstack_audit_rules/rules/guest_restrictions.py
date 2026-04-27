from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import is_enabled
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.guest-restrictions",
    title="Guest user restrictions missing",
    severity=Severity.MEDIUM,
    description=(
        "Tenant should have at least one enabled CA policy targeting guest "
        "or external users (via includeGuestsOrExternalUsers or a guests "
        "group) with stricter location, MFA, or block conditions."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/howto-policy-guest",
    ],
    remediation_hint=(
        "Add an enabled CA policy with includeGuestsOrExternalUsers or an "
        "explicit guest group, restricting locations or requiring MFA."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = []
    for policy in context.policies:
        if not is_enabled(policy):
            continue
        cond = policy.conditions.users if policy.conditions is not None else None
        if cond is None:
            continue
        if cond.include_guests_or_external_users:
            qualifying.append(policy)
            continue
        # Also count policies that target obvious guest groups by display-name match.
        if cond.include_groups:
            guest_group_ids = {
                g.id for g in context.groups if g.display_name and "guest" in g.display_name.lower()
            }
            if set(cond.include_groups) & guest_group_ids:
                qualifying.append(policy)
    if qualifying:
        return []
    return [
        make_finding(
            METADATA,
            tenant_id=context.tenant_id,
            affected_objects=[
                AffectedObject(type="tenant", id=context.tenant_id, display_name="tenant")
            ],
            summary="No enabled CA policy targets guest or external users.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
