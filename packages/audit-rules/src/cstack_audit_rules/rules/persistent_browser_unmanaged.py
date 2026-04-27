from cstack_audit_core import AffectedObject, Finding, Severity

from cstack_audit_rules._helpers import is_enabled
from cstack_audit_rules.context import AuditContext
from cstack_audit_rules.registry import Rule, RuleMetadata, make_finding, register_rule

METADATA = RuleMetadata(
    id="rule.persistent-browser-unmanaged",
    title="Persistent browser session control not configured",
    severity=Severity.LOW,
    description=(
        "Tenant should set a persistentBrowser session control on at least "
        "one enabled CA policy so unmanaged or BYOD sessions cannot persist."
    ),
    references=[
        "https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/howto-conditional-access-session-lifetime#persistent-browser-session",
    ],
    remediation_hint=(
        "Set sessionControls.persistentBrowser.mode to never on a CA policy "
        "targeting browser clients for BYOD or guest segments."
    ),
)


def _evaluate(context: AuditContext) -> list[Finding]:
    qualifying = [
        p
        for p in context.policies
        if is_enabled(p)
        and p.session_controls is not None
        and p.session_controls.persistent_browser is not None
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
            summary="No enabled CA policy configures persistentBrowser session control.",
            evidence={"qualifying_policies": 0},
            as_of=context.as_of,
        )
    ]


RULE = Rule(metadata=METADATA, evaluator=_evaluate)
register_rule(RULE)
