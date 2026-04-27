from datetime import timedelta

from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import ensure_utc
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.disabled-policies-old",
    title="Disabled policy aging in tenant",
    severity=Severity.INFO,
    description=(
        "Disabled CA policies modified more than 180 days ago should be "
        "deleted or re-enabled. Leaving them in place clutters the catalogue "
        "and obscures real intent."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/policy-management",
    ],
    remediation_hint=(
        "Delete disabled policies you no longer plan to enable, or document "
        "why they are kept dormant in the policy description."
    ),
)

_STALE_DAYS = 180


def _evaluate(context: AuditContext) -> list[Finding]:
    findings: list[Finding] = []
    threshold = context.as_of - timedelta(days=_STALE_DAYS)
    for policy in context.policies:
        if policy.state != "disabled":
            continue
        modified = policy.modified_date_time
        if modified is None or ensure_utc(modified) < threshold:
            findings.append(
                make_finding(
                    METADATA,
                    tenant_id=context.tenant_id,
                    affected_objects=[
                        AffectedObject(
                            type="policy", id=policy.id, display_name=policy.display_name
                        )
                    ],
                    summary=(
                        f"Disabled policy '{policy.display_name}' has been dormant for "
                        f"{_STALE_DAYS}+ days."
                    ),
                    evidence={
                        "policy_id": policy.id,
                        "modified_date_time": modified.isoformat() if modified else None,
                        "stale_days_threshold": _STALE_DAYS,
                    },
                    as_of=context.as_of,
                )
            )
    return findings


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
