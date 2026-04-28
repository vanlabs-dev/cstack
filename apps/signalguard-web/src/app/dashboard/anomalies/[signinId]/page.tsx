import { Shield } from 'lucide-react';

import { AnomalyActionBar } from '@/components/anomaly/AnomalyActionBar';
import { LocationCard } from '@/components/anomaly/LocationCard';
import { MetadataTable } from '@/components/anomaly/MetadataTable';
import { ShapWaterfall } from '@/components/anomaly/ShapWaterfall';
import { UserHistoryStrip } from '@/components/anomaly/UserHistoryStrip';
import { AppShell } from '@/components/layout/AppShell';
import { Avatar } from '@/components/system/Avatar';
import { SeverityBadge, type SeverityLevel } from '@/components/system/SeverityBadge';
import { callAnomalyDetail, callUserSignins } from '@/lib/api/calls';
import { formatRelativeTime } from '@/lib/format';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

import type { TenantSummary } from '@/lib/tenant';

interface DrillDownProps {
  params: Promise<{ signinId: string }>;
  searchParams: Promise<{ tenant?: string | string[] }>;
}

function tenantDisplayName(tenants: TenantSummary[], id: string): string {
  return tenants.find((t) => t.tenant_id === id)?.display_name ?? id;
}

function severityForScore(score: number): SeverityLevel {
  if (score >= 0.95) return 'crit';
  if (score >= 0.85) return 'high';
  if (score >= 0.7) return 'med';
  return 'low';
}

function summariseTypicalCountries(
  history: { location?: { countryOrRegion?: string | null } | null }[],
): string[] {
  const counts: Record<string, number> = {};
  for (const s of history) {
    const c = s.location?.countryOrRegion ?? null;
    if (!c) continue;
    counts[c] = (counts[c] ?? 0) + 1;
  }
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([k]) => k);
}

export default async function AnomalyDrillDownPage({ params, searchParams }: DrillDownProps) {
  const { signinId } = await params;
  const sp = await searchParams;
  const tenantParam = Array.isArray(sp.tenant) ? sp.tenant[0] : sp.tenant;

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
        <p className="text-fg-tertiary">No tenant selected.</p>
      </AppShell>
    );
  }

  const detail = await callAnomalyDetail(activeTenantId, signinId);
  const userId = detail.signin.userId;
  const history = await callUserSignins(activeTenantId, userId, { limit: 30 });
  const sortedHistory = [...history.items].sort(
    (a, b) => new Date(b.createdDateTime).getTime() - new Date(a.createdDateTime).getTime(),
  );
  const typicalCountries = summariseTypicalCountries(history.items).filter(
    (c) => c !== detail.signin.location?.countryOrRegion,
  );
  const severity = severityForScore(detail.score.normalised_score);
  const userDisplay = detail.signin.userPrincipalName ?? detail.signin.userId;

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
        { label: signinId.slice(0, 8) },
      ]}
    >
      <header className="mb-4 flex items-center gap-3">
        <Avatar name={userDisplay} size={36} />
        <div className="flex-1 min-w-0">
          <h1 className="truncate text-18 font-semibold tracking-[-0.005em]">{userDisplay}</h1>
          <div className="mono mt-0.5 text-11 text-fg-tertiary">
            {detail.signin.id} · {formatRelativeTime(detail.signin.createdDateTime)} ·{' '}
            {detail.signin.location?.countryOrRegion ?? '?'}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <SeverityBadge level={severity} />
          <div
            className="num mono text-22 font-semibold tracking-[-0.012em]"
            aria-label="anomaly score"
          >
            {(detail.score.normalised_score * 100).toFixed(0)}
          </div>
        </div>
      </header>

      <div className="grid gap-3.5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
        <MetadataTable signin={detail.signin} />
        <div className="flex flex-col gap-3">
          <LocationCard
            detail={detail}
            history={sortedHistory}
            typicalCountries={typicalCountries}
            distanceFromLastKm={null}
          />
          <ShapWaterfall
            contributions={detail.score.shap_top_features ?? []}
            baseScore={0.12}
            normalisedScore={detail.score.normalised_score}
          />
          <UserHistoryStrip
            signins={sortedHistory}
            tenantId={activeTenantId}
            highlightId={signinId}
          />
          <AnomalyActionBar detail={detail} />
        </div>
      </div>
    </AppShell>
  );
}
