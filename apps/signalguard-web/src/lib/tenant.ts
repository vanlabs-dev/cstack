/**
 * Tenant scope helpers. The active tenant is the URL search param
 * ``?tenant=<id>`` whenever it is present; pages without an explicit
 * tenant fall back to the first tenant the API returns.
 */

import { listTenantsTenantsGet } from '@/lib/api/generated';
import type { TenantSummary as GeneratedTenantSummary } from '@/lib/api/generated/types.gen';

import { apiClient } from './api/client';

export type TenantSummary = GeneratedTenantSummary;

export async function fetchTenantList(): Promise<TenantSummary[]> {
  const { data } = await listTenantsTenantsGet({
    client: apiClient(),
    throwOnError: true,
  });
  return data;
}

export async function resolveActiveTenantId(fromQuery: string | undefined): Promise<string | null> {
  if (fromQuery) return fromQuery;
  try {
    const tenants = await fetchTenantList();
    return tenants[0]?.tenant_id ?? null;
  } catch {
    return null;
  }
}
