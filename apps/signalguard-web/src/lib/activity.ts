/**
 * Cross-tenant recent activity feed.
 *
 * Walks each tenant in parallel, pulls the last few findings, then merges
 * by ``first_seen_at`` desc. The fixture corpus is small so n*per-tenant
 * is fine; a real-tenant deployment would push this into the API.
 */

import type { Finding } from '@/lib/api/generated/types.gen';

import { callListFindings } from './api/calls';
import type { TenantSummary } from './tenant';

export interface ActivityEntry {
  finding: Finding;
  tenant: TenantSummary;
}

export async function fetchRecentActivity(
  tenants: TenantSummary[],
  perTenantLimit = 5,
  totalLimit = 10,
): Promise<ActivityEntry[]> {
  if (tenants.length === 0) return [];
  const buckets = await Promise.all(
    tenants.map(async (t) => {
      try {
        const data = await callListFindings({
          tenantId: t.tenant_id,
          limit: perTenantLimit,
          offset: 0,
        });
        return data.items.map((finding: Finding) => ({ finding, tenant: t }));
      } catch {
        return [];
      }
    }),
  );
  const merged = buckets.flat();
  merged.sort((a, b) => {
    const aT = a.finding.first_seen_at ?? '';
    const bT = b.finding.first_seen_at ?? '';
    return bT.localeCompare(aT);
  });
  return merged.slice(0, totalLimit);
}

export function totalsFromActivity(entries: ActivityEntry[]): {
  open: number;
  critical: number;
} {
  const critical = entries.filter((e) => e.finding.severity === 'CRITICAL').length;
  return { open: entries.length, critical };
}
