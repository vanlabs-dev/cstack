import type {
  AnomalyScore,
  AnomalyScoreDetail,
  ApiKeySummary,
  CoverageMatrix,
  Finding,
  FindingsSummary,
  ModelSummary,
  PaginatedAnomalyScore,
  PaginatedFinding,
  PaginatedSignIn,
  SigninStats,
  TenantDetail,
} from '@/lib/api/generated/types.gen';
import type { TenantSummary } from '@/lib/tenant';

export const TENANT_A_ID = '00000000-aaaa-1111-1111-111111111111';
export const TENANT_B_ID = '00000000-bbbb-2222-2222-222222222222';

export const tenantA: TenantSummary = {
  tenant_id: TENANT_A_ID,
  display_name: 'tenant-a',
  is_fixture: true,
  added_at: '2026-04-01T00:00:00Z',
  last_extract_at: '2026-04-28T00:00:00Z',
  last_audit_at: '2026-04-28T00:30:00Z',
  last_anomaly_score_at: '2026-04-28T01:00:00Z',
  api_key_count: 1,
};

export const tenantB: TenantSummary = {
  tenant_id: TENANT_B_ID,
  display_name: 'tenant-b',
  is_fixture: true,
  added_at: '2026-04-01T00:00:00Z',
  last_extract_at: '2026-04-28T00:00:00Z',
  last_audit_at: '2026-04-28T00:30:00Z',
  last_anomaly_score_at: null,
  api_key_count: 0,
};

export const tenantADetail: TenantDetail = { ...tenantA };

export function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 'f-' + Math.random().toString(16).slice(2, 10),
    tenant_id: TENANT_A_ID,
    rule_id: 'rule.mfa-all-users',
    category: 'rule',
    severity: 'HIGH',
    title: 'MFA not enforced for all users',
    summary:
      'No enabled CA policy targets the All users group with MFA. This breaks the closed-loop assumption.',
    affected_objects: [{ type: 'policy', id: 'pol-1', display_name: 'Require_MFA_All_Users' }],
    evidence: { policyId: 'pol-1' },
    remediation_hint: 'Enable Require_MFA_All_Users for the All users group.',
    references: ['https://learn.microsoft.com/'],
    detected_at: '2026-04-28T00:00:00Z',
    first_seen_at: '2026-04-28T00:00:00Z',
    ...overrides,
  };
}

export function makePaginatedFindings(items?: Finding[]): PaginatedFinding {
  const list =
    items ??
    (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const).map((sev, i) =>
      makeFinding({ id: `f-${i}`, severity: sev, title: `${sev} finding` }),
    );
  return { items: list, total: list.length, limit: 25, offset: 0, has_more: false };
}

export const findingsSummary: FindingsSummary = {
  total: 12,
  by_severity: { CRITICAL: 2, HIGH: 4, MEDIUM: 3, LOW: 2, INFO: 1 },
  by_category: { coverage: 3, rule: 6, exclusion: 3 },
  by_rule_id: { 'rule.mfa-all-users': 1, 'rule.block-legacy-auth': 2 },
  generated_at: '2026-04-28T00:00:00Z',
};

export function makeAnomalyScore(overrides: Partial<AnomalyScore> = {}): AnomalyScore {
  return {
    tenant_id: TENANT_A_ID,
    signin_id: 'signin-' + Math.random().toString(16).slice(2, 8),
    user_id: 'user-tenant-a-0001',
    model_name: 'signalguard-anomaly-pooled-test',
    model_version: '1',
    raw_score: -0.42,
    normalised_score: 0.95,
    is_anomaly: true,
    shap_top_features: [
      {
        feature_name: 'travel_speed_kmh',
        feature_value: 8000,
        shap_value: -0.42,
        direction: 'pushes_anomalous',
      },
      {
        feature_name: 'is_new_country_for_user',
        feature_value: 1,
        shap_value: -0.31,
        direction: 'pushes_anomalous',
      },
      {
        feature_name: 'mfa_satisfied',
        feature_value: 1,
        shap_value: 0.18,
        direction: 'pushes_normal',
      },
    ],
    scored_at: '2026-04-28T00:00:00Z',
    ...overrides,
  };
}

export const anomalyScores: AnomalyScore[] = [
  makeAnomalyScore({ signin_id: 'signin-1', normalised_score: 0.97 }),
  makeAnomalyScore({ signin_id: 'signin-2', normalised_score: 0.86 }),
  makeAnomalyScore({ signin_id: 'signin-3', normalised_score: 0.72 }),
];

export const paginatedScores: PaginatedAnomalyScore = {
  items: anomalyScores,
  total: 3,
  limit: 50,
  offset: 0,
  has_more: false,
};

export const anomalyDetail: AnomalyScoreDetail = {
  score: anomalyScores[0]!,
  signin: {
    id: 'signin-1',
    createdDateTime: '2026-04-28T00:00:00Z',
    userId: 'user-tenant-a-0001',
    userPrincipalName: 'h.roe@northwind.local',
    appDisplayName: 'Office 365 Exchange Online',
    appId: 'app-1',
    clientAppUsed: 'Browser',
    deviceDetail: {
      deviceId: 'dev-1',
      operatingSystem: 'macOS 14.4',
      browser: 'Chrome 132',
      isCompliant: false,
      isManaged: false,
      trustType: null,
    },
    location: {
      city: 'Manchester',
      countryOrRegion: 'GB',
      state: 'England',
      geoCoordinates: { latitude: 53.48, longitude: -2.24 },
    },
    ipAddress: '84.92.18.114',
    status: { errorCode: 0, failureReason: null, additionalDetails: null },
    riskLevelDuringSignIn: 'high',
    riskLevelAggregated: 'high',
    riskState: 'atRisk',
    conditionalAccessStatus: 'notApplied',
    authenticationRequirement: 'multiFactorAuthentication',
    authenticationMethodsUsed: ['password'],
    isInteractive: true,
  },
  finding: null,
};

export const userSignins: PaginatedSignIn = {
  items: Array.from({ length: 8 }, (_, i) => ({
    ...anomalyDetail.signin,
    id: `history-${i}`,
    createdDateTime: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
  })),
  total: 8,
  limit: 30,
  offset: 0,
  has_more: false,
};

export const coverageMatrix: CoverageMatrix = {
  tenant_id: TENANT_A_ID,
  computed_at: '2026-04-28T00:00:00Z',
  cells: [
    {
      user_segment: 'all_users',
      app_segment: 'm365_core',
      protection_level: 3,
      applicable_policy_ids: ['pol-1'],
      member_count: 247,
    },
    {
      user_segment: 'all_users',
      app_segment: 'admin_portals',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 247,
    },
    {
      user_segment: 'all_users',
      app_segment: 'legacy_auth',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 247,
    },
    {
      user_segment: 'all_users',
      app_segment: 'high_risk_apps',
      protection_level: 2,
      applicable_policy_ids: [],
      member_count: 247,
    },
    {
      user_segment: 'all_users',
      app_segment: 'all_apps',
      protection_level: 1,
      applicable_policy_ids: ['pol-3'],
      member_count: 247,
    },
    {
      user_segment: 'admins_any',
      app_segment: 'm365_core',
      protection_level: 4,
      applicable_policy_ids: ['pol-1'],
      member_count: 12,
    },
    {
      user_segment: 'admins_any',
      app_segment: 'admin_portals',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 12,
    },
    {
      user_segment: 'admins_any',
      app_segment: 'legacy_auth',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 12,
    },
    {
      user_segment: 'admins_any',
      app_segment: 'high_risk_apps',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 12,
    },
    {
      user_segment: 'admins_any',
      app_segment: 'all_apps',
      protection_level: 3,
      applicable_policy_ids: ['pol-1'],
      member_count: 12,
    },
    {
      user_segment: 'privileged_roles',
      app_segment: 'm365_core',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 8,
    },
    {
      user_segment: 'privileged_roles',
      app_segment: 'admin_portals',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 8,
    },
    {
      user_segment: 'privileged_roles',
      app_segment: 'legacy_auth',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 8,
    },
    {
      user_segment: 'privileged_roles',
      app_segment: 'high_risk_apps',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 8,
    },
    {
      user_segment: 'privileged_roles',
      app_segment: 'all_apps',
      protection_level: 4,
      applicable_policy_ids: ['pol-2'],
      member_count: 8,
    },
    {
      user_segment: 'guests',
      app_segment: 'm365_core',
      protection_level: 2,
      applicable_policy_ids: [],
      member_count: 34,
    },
    {
      user_segment: 'guests',
      app_segment: 'admin_portals',
      protection_level: 1,
      applicable_policy_ids: [],
      member_count: 34,
    },
    {
      user_segment: 'guests',
      app_segment: 'legacy_auth',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 34,
    },
    {
      user_segment: 'guests',
      app_segment: 'high_risk_apps',
      protection_level: 2,
      applicable_policy_ids: [],
      member_count: 34,
    },
    {
      user_segment: 'guests',
      app_segment: 'all_apps',
      protection_level: 2,
      applicable_policy_ids: [],
      member_count: 34,
    },
    {
      user_segment: 'service_accounts',
      app_segment: 'm365_core',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 18,
    },
    {
      user_segment: 'service_accounts',
      app_segment: 'admin_portals',
      protection_level: 1,
      applicable_policy_ids: [],
      member_count: 18,
    },
    {
      user_segment: 'service_accounts',
      app_segment: 'legacy_auth',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 18,
    },
    {
      user_segment: 'service_accounts',
      app_segment: 'high_risk_apps',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 18,
    },
    {
      user_segment: 'service_accounts',
      app_segment: 'all_apps',
      protection_level: 0,
      applicable_policy_ids: [],
      member_count: 18,
    },
  ],
};

export const signinStats: SigninStats = {
  tenant_id: TENANT_A_ID,
  total: 1234,
  distinct_users: 47,
  earliest_at: '2026-03-01T00:00:00Z',
  latest_at: '2026-04-28T00:00:00Z',
  success_count: 1100,
  failure_count: 134,
  top_countries: [
    ['GB', 800],
    ['US', 200],
  ],
  top_apps: [
    ['Office 365 Exchange Online', 700],
    ['Microsoft Teams', 400],
  ],
};

export const modelSummary: ModelSummary[] = [
  {
    name: 'signalguard-anomaly-pooled-' + TENANT_A_ID,
    current_champion_version: '2',
    current_challenger_version: '3',
    last_trained_at: '2026-04-28T00:00:00Z',
    training_metrics: {
      n_signins_used: 10528,
      training_duration_seconds: 3.8,
      precision: 0.78,
      recall: 0.91,
    },
  },
];

export const apiKeys: ApiKeySummary[] = [{ label: 'ci', created_at: '2026-04-01T00:00:00Z' }];
