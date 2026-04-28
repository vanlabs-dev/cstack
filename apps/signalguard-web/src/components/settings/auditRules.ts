/**
 * Static catalogue of the 15 CA audit rules registered in
 * cstack-audit-rules. Mirrors docs/RULES.md so the settings page can render
 * the list without an API endpoint. Promote to a /audit/rules endpoint
 * once one exists.
 */

import type { AuditRuleData } from './AuditRuleRow';

export const AUDIT_RULES: AuditRuleData[] = [
  {
    id: 'rule.mfa-all-users',
    title: 'MFA enforced for all users',
    severity: 'CRITICAL',
    category: 'coverage',
    description:
      'There must be at least one enabled CA policy that requires MFA for the All users group with no broad exclusions. Without it, the tenant has no closed-loop MFA assumption.',
    references: [
      'https://learn.microsoft.com/en-us/azure/active-directory/conditional-access/concept-conditional-access-policy-common',
    ],
  },
  {
    id: 'rule.mfa-admins',
    title: 'MFA enforced for administrators',
    severity: 'CRITICAL',
    category: 'coverage',
    description:
      'Every directory role member must be covered by an enabled CA policy that requires MFA. Admin-tier compromise is the most damaging attack path.',
    references: ['https://www.cisecurity.org/benchmark/microsoft_365'],
  },
  {
    id: 'rule.block-legacy-auth',
    title: 'Legacy authentication blocked',
    severity: 'HIGH',
    category: 'rule',
    description:
      'No enabled policy permits client app types other than browser, mobileAppsAndDesktopClients, or modern auth. Legacy protocols bypass MFA challenges.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/conditional-access/'],
  },
  {
    id: 'rule.compliant-device-admin-actions',
    title: 'Admin actions require compliant device',
    severity: 'HIGH',
    category: 'rule',
    description:
      'Privileged role assignments and high-risk apps must require a compliant or hybrid-joined device.',
    references: [
      'https://www.ncsc.gov.uk/collection/cloud-security/implementing-the-cloud-security-principles',
    ],
  },
  {
    id: 'rule.device-compliance-sensitive-apps',
    title: 'Device compliance for sensitive apps',
    severity: 'HIGH',
    category: 'rule',
    description:
      'Sensitive workloads (Azure Management, Exchange Admin, key vaults) require compliant-device grant controls.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/conditional-access/'],
  },
  {
    id: 'rule.risk-based-signin',
    title: 'Risk-based sign-in protection',
    severity: 'HIGH',
    category: 'rule',
    description: 'A CA policy must escalate at-risk sign-ins (medium or higher) to MFA or block.',
    references: [
      'https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-risks',
    ],
  },
  {
    id: 'rule.risk-based-user',
    title: 'Risk-based user protection',
    severity: 'HIGH',
    category: 'rule',
    description: 'Users marked at-risk must be challenged with a password change or blocked.',
    references: ['https://learn.microsoft.com/en-us/entra/id-protection/'],
  },
  {
    id: 'rule.signin-frequency-unmanaged',
    title: 'Sign-in frequency on unmanaged devices',
    severity: 'MEDIUM',
    category: 'rule',
    description:
      'Sessions on unmanaged devices should require reauth at most every 24h to limit token lifetime.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/conditional-access/'],
  },
  {
    id: 'rule.persistent-browser-unmanaged',
    title: 'Persistent browser sessions on unmanaged devices',
    severity: 'MEDIUM',
    category: 'rule',
    description: 'Disable persistent browser sessions on unmanaged devices to avoid stale tokens.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/conditional-access/'],
  },
  {
    id: 'rule.guest-restrictions',
    title: 'Guest user restrictions',
    severity: 'MEDIUM',
    category: 'rule',
    description: 'Guests must be limited to specific apps and challenged with MFA.',
    references: ['https://www.cisecurity.org/benchmark/microsoft_365'],
  },
  {
    id: 'rule.workload-identity-policies',
    title: 'Workload identity policies',
    severity: 'MEDIUM',
    category: 'rule',
    description: 'Service principals and managed identities require their own CA scoping.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/conditional-access/'],
  },
  {
    id: 'rule.report-only-graduated',
    title: 'Report-only policies have graduated',
    severity: 'MEDIUM',
    category: 'rule',
    description:
      'Policies in report-only mode for >90 days should either be enabled or removed. Report-only never enforces.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/conditional-access/'],
  },
  {
    id: 'rule.disabled-policies-old',
    title: 'Disabled policies are recent',
    severity: 'LOW',
    category: 'rule',
    description:
      'Disabled policies older than 180 days should be removed; they are confusing dead weight.',
    references: ['https://www.cisecurity.org/benchmark/microsoft_365'],
  },
  {
    id: 'rule.trusted-locations-defined',
    title: 'Trusted locations are defined and narrow',
    severity: 'MEDIUM',
    category: 'rule',
    description:
      'Trusted IP ranges should be specific (smaller than /24) and named locations should be present.',
    references: ['https://www.cisecurity.org/benchmark/microsoft_365'],
  },
  {
    id: 'rule.breakglass-configured',
    title: 'Break-glass accounts configured',
    severity: 'HIGH',
    category: 'rule',
    description:
      'Two break-glass accounts must exist and be excluded from MFA policies, with monitoring on every sign-in.',
    references: ['https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/'],
  },
];
