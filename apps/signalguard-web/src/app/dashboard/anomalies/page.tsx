import { Play, Shield } from 'lucide-react';

import { AnomalyList, type AnomalyListSigninExtras } from '@/components/anomaly-feed/AnomalyList';
import { FilterRail } from '@/components/anomaly-feed/FilterRail';
import { Pagination } from '@/components/findings/Pagination';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/Button';
import { callAnomalyDetail, callListAnomalyScores } from '@/lib/api/calls';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

import type { TenantSummary } from '@/lib/tenant';

interface AnomalyFeedProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

function pickFirst(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function tenantDisplayName(tenants: TenantSummary[], id: string): string {
  return tenants.find((t) => t.tenant_id === id)?.display_name ?? id;
}

export default async function AnomalyFeedPage({ searchParams }: AnomalyFeedProps) {
  const params = await searchParams;
  const tenantParam = pickFirst(params.tenant);

  const tenants = await fetchTenantList();
  const activeTenantId = await resolveActiveTenantId(tenantParam);
  if (!activeTenantId) {
    return (
      <AppShell
        tenants={tenants}
        activeTenantId={null}
        crumbs={[
          {
            label: 'SignalGuard',
            pill: true,
            pillIcon: Shield,
            pillBg: 'var(--color-sg-subtle)',
            pillFg: 'var(--color-sg-text)',
          },
          { label: 'Anomalies' },
        ]}
      >
        <p className="text-13 text-fg-tertiary">No tenant selected.</p>
      </AppShell>
    );
  }

  const minScoreRaw = pickFirst(params.min_score);
  const minScore = minScoreRaw ? Number(minScoreRaw) : undefined;
  const since = pickFirst(params.since);
  const userId = pickFirst(params.user_id);
  const limit = Math.min(Math.max(parseInt(pickFirst(params.limit) ?? '50', 10) || 50, 1), 200);
  const offset = Math.max(parseInt(pickFirst(params.offset) ?? '0', 10) || 0, 0);

  const page = await callListAnomalyScores(activeTenantId, {
    min_score: minScore,
    since,
    user_id: userId,
    is_anomaly: minScore && minScore >= 0.7 ? true : undefined,
    limit,
    offset,
  });

  // Pull a small batch of detail bundles so we can fill in upn/country/device.
  // Cap the parallel fetches to keep the request cheap.
  const detailLookup: Record<string, AnomalyListSigninExtras> = {};
  const enrichTargets = page.items.slice(0, 24);
  const details = await Promise.all(
    enrichTargets.map((s) => callAnomalyDetail(activeTenantId, s.signin_id).catch(() => null)),
  );
  for (const detail of details) {
    if (detail) {
      const id = detail.signin.id;
      const device = detail.signin.deviceDetail
        ? [detail.signin.deviceDetail.operatingSystem, detail.signin.deviceDetail.browser]
            .filter(Boolean)
            .join(' · ')
        : null;
      detailLookup[id] = {
        upn: detail.signin.userPrincipalName,
        country: detail.signin.location?.countryOrRegion,
        city: detail.signin.location?.city,
        device,
      };
    }
  }

  return (
    <AppShell
      tenants={tenants}
      activeTenantId={activeTenantId}
      crumbs={[
        {
          label: 'SignalGuard',
          pill: true,
          pillIcon: Shield,
          pillBg: 'var(--color-sg-subtle)',
          pillFg: 'var(--color-sg-text)',
        },
        { label: tenantDisplayName(tenants, activeTenantId) },
        { label: 'Anomalies' },
      ]}
      actions={
        <>
          <Button variant="default" size="default" aria-label="Score now">
            <Play size={11} strokeWidth={1.7} aria-hidden />
            Score now
          </Button>
          <Button
            variant="primary"
            size="default"
            aria-label="Score window"
            title="Window picker lands in 5b polish"
          >
            <Play size={11} strokeWidth={1.7} aria-hidden />
            Score window…
          </Button>
        </>
      }
    >
      <div className="mb-4">
        <p className="eyebrow mb-1.5">Behavioural ML · 60-day baseline</p>
        <h1 className="text-22 font-semibold tracking-[-0.012em]">Sign-in anomalies</h1>
        <p className="mt-1 max-w-[640px] text-13 text-fg-tertiary">
          Each row is a sign-in scored against the user&apos;s baseline. Triage the queue and feed
          back known-good labels in 5b once mutation endpoints land.
        </p>
      </div>

      <FilterRail />

      <AnomalyList scores={page.items} signinExtras={detailLookup} tenantId={activeTenantId} />

      <Pagination total={page.total} limit={limit} offset={offset} hasMore={page.has_more} />
    </AppShell>
  );
}
