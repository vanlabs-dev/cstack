"""Sign-in synthesizer.

Produces realistic Graph-shaped sign-in events that the existing SignIn
pydantic model can parse. ``signins`` builds a baseline; ``anomalies``
injects scripted attack patterns; ``scenarios`` strings them together
per fixture tenant.
"""

from cstack_fixtures.synth.anomalies import (
    inject_credential_stuffing_burst,
    inject_impossible_travel,
    inject_mfa_bypass,
    inject_new_asn,
    inject_off_hours_admin_action,
)
from cstack_fixtures.synth.scenarios import (
    Scenario,
    ScenarioName,
    scenarios_for_tenant,
)
from cstack_fixtures.synth.signins import (
    SyntheticUserProfile,
    synthesize_baseline_signins,
)

__all__ = [
    "Scenario",
    "ScenarioName",
    "SyntheticUserProfile",
    "inject_credential_stuffing_burst",
    "inject_impossible_travel",
    "inject_mfa_bypass",
    "inject_new_asn",
    "inject_off_hours_admin_action",
    "scenarios_for_tenant",
    "synthesize_baseline_signins",
]
