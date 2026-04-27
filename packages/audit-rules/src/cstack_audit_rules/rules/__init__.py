"""Rule modules. Importing this package populates the RULE_REGISTRY."""

# Side-effect imports: each module registers its rule on import.
from cstack_audit_rules.rules import (  # noqa: F401
    block_legacy_auth,
    breakglass_configured,
    compliant_device_admin_actions,
    device_compliance_sensitive_apps,
    disabled_policies_old,
    guest_restrictions,
    mfa_admins,
    mfa_all_users,
    persistent_browser_unmanaged,
    report_only_graduated,
    risk_based_signin,
    risk_based_user,
    signin_frequency_unmanaged,
    trusted_locations_defined,
    workload_identity_policies,
)
