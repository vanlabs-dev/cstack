/**
 * Thin typed wrappers around the generated SDK functions.
 *
 * The generated openapi-ts client narrows ``data`` to the union of the
 * response object's property types under some configurations. The wrappers
 * here re-cast to the intended response type so call sites stay typed.
 * This is a one-way ratchet: edit this file when the OpenAPI spec gains
 * new endpoints, never edit ``generated/`` directly.
 */

import {
  createApiKeyTenantsTenantIdApiKeysPost,
  deleteApiKeyTenantsTenantIdApiKeysKeyLabelDelete,
  feedTenantsTenantIdAnomalyScoresFeedGet,
  findingsSummaryTenantsTenantIdFindingsSummaryGet,
  getCoverageTenantsTenantIdCoverageMatrixGet,
  getDetailTenantsTenantIdAnomalyScoresSigninIdGet,
  getFindingTenantsTenantIdFindingsFindingIdGet,
  getNarrativeTenantsTenantIdFindingsFindingIdNarrativeGet,
  getStatsTenantsTenantIdSigninsStatsGet,
  getTenantDetailTenantsTenantIdGet,
  getUserSigninsTenantsTenantIdUsersUserIdSigninsGet,
  listApiKeysTenantsTenantIdApiKeysGet,
  listFindingsTenantsTenantIdFindingsGet,
  listModelsTenantsTenantIdModelsGet,
  listScoresTenantsTenantIdAnomalyScoresGet,
  listTenantsTenantsGet,
  regenerateNarrativeTenantsTenantIdFindingsFindingIdNarrativeRegeneratePost,
  runAuditTenantsTenantIdAuditRunPost,
  scoreTenantsTenantIdAnomalyScorePost,
  whoamiWhoamiGet,
} from '@/lib/api/generated';
import type {
  AnomalyScore,
  AnomalyScoreDetail,
  AnomalyScoreRequest,
  AnomalyScoreRunResponse,
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
  ApiCaller,
  ApiKeySummary,
  AuditRunRequest,
  AuditRunResponse,
  CoverageMatrix,
  Finding,
  FindingsSummary,
  ModelSummary,
  NarrativeResponse,
  PaginatedAnomalyScore,
  PaginatedFinding,
  PaginatedSignIn,
  RegenerateRequest,
  SigninStats,
  TenantDetail,
  TenantSummary,
} from '@/lib/api/generated/types.gen';

import { apiClient } from './client';

interface WithAbort {
  signal?: AbortSignal;
}

interface FindingsListQuery extends WithAbort {
  tenantId: string;
  category?: Array<'coverage' | 'rule' | 'exclusion' | 'anomaly'>;
  minSeverity?: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  ruleId?: string;
  since?: string;
  limit?: number;
  offset?: number;
}

export async function callWhoami(opts: WithAbort = {}): Promise<ApiCaller> {
  const { data } = await whoamiWhoamiGet({
    client: apiClient(),
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as ApiCaller;
}

export async function callListTenants(opts: WithAbort = {}): Promise<TenantSummary[]> {
  const { data } = await listTenantsTenantsGet({
    client: apiClient(),
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as TenantSummary[];
}

export async function callTenantDetail(
  tenantId: string,
  opts: WithAbort = {},
): Promise<TenantDetail> {
  const { data } = await getTenantDetailTenantsTenantIdGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as TenantDetail;
}

export async function callListFindings(q: FindingsListQuery): Promise<PaginatedFinding> {
  const { data } = await listFindingsTenantsTenantIdFindingsGet({
    client: apiClient(),
    path: { tenant_id: q.tenantId },
    query: {
      category: q.category,
      min_severity: q.minSeverity,
      rule_id: q.ruleId,
      since: q.since,
      limit: q.limit,
      offset: q.offset,
    },
    signal: q.signal,
    throwOnError: true,
  });
  return data as unknown as PaginatedFinding;
}

export async function callFinding(
  tenantId: string,
  findingId: string,
  opts: WithAbort = {},
): Promise<Finding> {
  const { data } = await getFindingTenantsTenantIdFindingsFindingIdGet({
    client: apiClient(),
    path: { tenant_id: tenantId, finding_id: findingId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as Finding;
}

export async function callFindingNarrative(
  tenantId: string,
  findingId: string,
  opts: WithAbort = {},
): Promise<NarrativeResponse> {
  const { data } = await getNarrativeTenantsTenantIdFindingsFindingIdNarrativeGet({
    client: apiClient(),
    path: { tenant_id: tenantId, finding_id: findingId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as NarrativeResponse;
}

export async function callRegenerateFindingNarrative(
  tenantId: string,
  findingId: string,
  body: RegenerateRequest = { prompt_version: 'v1' },
  opts: WithAbort = {},
): Promise<NarrativeResponse> {
  const { data } = await regenerateNarrativeTenantsTenantIdFindingsFindingIdNarrativeRegeneratePost(
    {
      client: apiClient(),
      path: { tenant_id: tenantId, finding_id: findingId },
      body,
      signal: opts.signal,
      throwOnError: true,
    },
  );
  return data as unknown as NarrativeResponse;
}

export async function callFindingsSummary(
  tenantId: string,
  opts: WithAbort = {},
): Promise<FindingsSummary> {
  const { data } = await findingsSummaryTenantsTenantIdFindingsSummaryGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as FindingsSummary;
}

export async function callListAnomalyScores(
  tenantId: string,
  query?: {
    user_id?: string;
    min_score?: number;
    is_anomaly?: boolean;
    since?: string;
    limit?: number;
    offset?: number;
  },
  opts: WithAbort = {},
): Promise<PaginatedAnomalyScore> {
  const { data } = await listScoresTenantsTenantIdAnomalyScoresGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    query,
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as PaginatedAnomalyScore;
}

export async function callAnomalyFeed(
  tenantId: string,
  query?: { n?: number; min_score?: number },
  opts: WithAbort = {},
): Promise<AnomalyScore[]> {
  const { data } = await feedTenantsTenantIdAnomalyScoresFeedGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    query,
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as AnomalyScore[];
}

export async function callAnomalyDetail(
  tenantId: string,
  signinId: string,
  opts: WithAbort = {},
): Promise<AnomalyScoreDetail> {
  const { data } = await getDetailTenantsTenantIdAnomalyScoresSigninIdGet({
    client: apiClient(),
    path: { tenant_id: tenantId, signin_id: signinId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as AnomalyScoreDetail;
}

export async function callCoverageMatrix(
  tenantId: string,
  opts: WithAbort = {},
): Promise<CoverageMatrix> {
  const { data } = await getCoverageTenantsTenantIdCoverageMatrixGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as CoverageMatrix;
}

export async function callSigninStats(
  tenantId: string,
  opts: WithAbort = {},
): Promise<SigninStats> {
  const { data } = await getStatsTenantsTenantIdSigninsStatsGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as SigninStats;
}

export async function callUserSignins(
  tenantId: string,
  userId: string,
  query?: { limit?: number; offset?: number },
  opts: WithAbort = {},
): Promise<PaginatedSignIn> {
  const { data } = await getUserSigninsTenantsTenantIdUsersUserIdSigninsGet({
    client: apiClient(),
    path: { tenant_id: tenantId, user_id: userId },
    query,
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as PaginatedSignIn;
}

export async function callRunAudit(
  tenantId: string,
  body: AuditRunRequest,
  opts: WithAbort = {},
): Promise<AuditRunResponse> {
  const { data } = await runAuditTenantsTenantIdAuditRunPost({
    client: apiClient(),
    path: { tenant_id: tenantId },
    body,
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as AuditRunResponse;
}

export async function callScoreAnomaly(
  tenantId: string,
  body: AnomalyScoreRequest,
  opts: WithAbort = {},
): Promise<AnomalyScoreRunResponse> {
  const { data } = await scoreTenantsTenantIdAnomalyScorePost({
    client: apiClient(),
    path: { tenant_id: tenantId },
    body,
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as AnomalyScoreRunResponse;
}

export async function callListModels(
  tenantId: string,
  opts: WithAbort = {},
): Promise<ModelSummary[]> {
  const { data } = await listModelsTenantsTenantIdModelsGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as ModelSummary[];
}

export async function callListApiKeys(
  tenantId: string,
  opts: WithAbort = {},
): Promise<ApiKeySummary[]> {
  const { data } = await listApiKeysTenantsTenantIdApiKeysGet({
    client: apiClient(),
    path: { tenant_id: tenantId },
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as ApiKeySummary[];
}

export async function callCreateApiKey(
  tenantId: string,
  body: ApiKeyCreateRequest,
  opts: WithAbort = {},
): Promise<ApiKeyCreateResponse> {
  const { data } = await createApiKeyTenantsTenantIdApiKeysPost({
    client: apiClient(),
    path: { tenant_id: tenantId },
    body,
    signal: opts.signal,
    throwOnError: true,
  });
  return data as unknown as ApiKeyCreateResponse;
}

export async function callDeleteApiKey(
  tenantId: string,
  keyLabel: string,
  opts: WithAbort = {},
): Promise<void> {
  await deleteApiKeyTenantsTenantIdApiKeysKeyLabelDelete({
    client: apiClient(),
    path: { tenant_id: tenantId, key_label: keyLabel },
    signal: opts.signal,
    throwOnError: true,
  });
}
