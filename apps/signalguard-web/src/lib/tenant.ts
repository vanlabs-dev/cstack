/**
 * Tenant scope helpers. The active tenant is the URL search param
 * ``?tenant=<id>`` whenever it is present; pages without an explicit
 * tenant fall back to the first tenant the API returns.
 */

import type { TenantSummary as GeneratedTenantSummary } from '@/lib/api/generated/types.gen';

import { callListTenants } from './api/calls';

export type TenantSummary = GeneratedTenantSummary;

export async function fetchTenantList(): Promise<TenantSummary[]> {
  return callListTenants();
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
