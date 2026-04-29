# Rules catalogue

> See [docs/INDEX.md](./INDEX.md) for the full documentation map.

15 best-practice CA rules ship in `packages/audit-rules`. Each rule is a
pure function that takes an `AuditContext` and returns zero or more
findings. Add a new rule by following the recipe in
[ARCHITECTURE.md](./ARCHITECTURE.md#adding-a-new-rule).

| id                                    | severity | description                                                                          |
| ------------------------------------- | -------- | ------------------------------------------------------------------------------------ |
| rule.block-legacy-auth                | HIGH     | At least one enabled CA policy blocks legacy auth client app types for all users.    |
| rule.mfa-all-users                    | HIGH     | At least one enabled CA policy targets All users with MFA as a grant control.        |
| rule.mfa-admins                       | CRITICAL | A dedicated CA policy targets privileged role members with MFA.                      |
| rule.risk-based-signin                | HIGH     | A CA policy uses signInRiskLevels (medium or high) to challenge risky sessions.      |
| rule.risk-based-user                  | HIGH     | A CA policy uses userRiskLevels (high) and forces password change.                   |
| rule.compliant-device-admin-actions   | MEDIUM   | Admin role members are required to use a compliant or HAADJ device.                  |
| rule.trusted-locations-defined        | LOW      | Tenant has at least one trusted IP named location.                                   |
| rule.device-compliance-sensitive-apps | MEDIUM   | Sensitive apps (Azure Portal, Graph PowerShell, SharePoint) require compliantDevice. |
| rule.signin-frequency-unmanaged       | LOW      | At least one CA policy sets a signInFrequency session control.                       |
| rule.persistent-browser-unmanaged     | LOW      | At least one CA policy sets a persistentBrowser session control.                     |
| rule.guest-restrictions               | MEDIUM   | A CA policy targets guest or external users with stricter conditions.                |
| rule.workload-identity-policies       | MEDIUM   | A CA policy uses clientApplications conditions to scope workload identities.         |
| rule.breakglass-configured            | HIGH     | At least one policy excludes a recognisable break-glass group.                       |
| rule.report-only-graduated            | LOW      | Per-policy: report-only state untouched for 180+ days.                               |
| rule.disabled-policies-old            | INFO     | Per-policy: disabled state untouched for 180+ days.                                  |

## References across all rules

- Microsoft Learn: <https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/>
- CISA SCuBA: <https://www.cisa.gov/scuba>
- CIS M365 Foundations: <https://www.cisecurity.org/benchmark/microsoft_365>
- NCSC NZ guidance: <https://www.ncsc.govt.nz/guidance/>

## Coverage matrix and exclusion hygiene

In addition to the 15 rules, the CLI's `audit coverage` command emits
`coverage.<user-segment>-on-<app-segment>` findings for cells that resolve
to no MFA-equivalent control, and `audit exclusions` emits
`exclusion.stale-user`, `exclusion.orphan-user`,
`exclusion.admin-mfa-bypass`, `exclusion.creep`, and
`exclusion.undocumented`. Both layers respect the same Severity scale.
