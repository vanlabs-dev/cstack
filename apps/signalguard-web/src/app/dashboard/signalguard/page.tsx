import { ArrowRight, Play, RefreshCw, Shield } from 'lucide-react';
import Link from 'next/link';

import { AnomalySummaryRow } from '@/components/overview/AnomalySummaryRow';
import { CoverageMatrixPreview } from '@/components/overview/CoverageMatrixPreview';
import { DataFreshnessPanel } from '@/components/overview/DataFreshnessPanel';
import { KpiCard } from '@/components/overview/KpiCard';
import { SeverityBreakdownBar } from '@/components/overview/SeverityBreakdownBar';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/Button';
import {
  callAnomalyFeed,
  callCoverageMatrix,
  callFindingsSummary,
  callListModels,
  callTenantDetail,
} from '@/lib/api/calls';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

import type { ModelSummary, TenantDetail } from '@/lib/api/generated/types.gen';
import type { TenantSummary } from '@/lib/tenant';

interface OverviewPageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

function tenantDisplayName(tenants: TenantSummary[], id: string): string {
  return tenants.find((t) => t.tenant_id === id)?.display_name ?? id;
}

function topCategories(byCategory: Record<string, number>): Array<[string, number]> {
  return Object.entries(byCategory)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
}

function approxTrend(total: number, length = 14): number[] {
  if (total === 0) return Array.from({ length }, () => 0);
  const series: number[] = [];
  for (let i = 0; i < length; i++) {
    const wobble = ((i * 37) % 5) - 2;
    series.push(Math.max(0, total + wobble));
  }
  return series;
}

export default async function SignalGuardOverviewPage({ searchParams }: OverviewPageProps) {
  const params = await searchParams;
  const tenantParam = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;

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
          { label: 'Overview' },
        ]}
      >
        <p className="text-13 text-fg-tertiary">
          No tenant in scope. Pick a tenant in the sidebar to view its overview.
        </p>
      </AppShell>
    );
  }

  const [tenantDetail, summary, anomalyFeed, matrix, models] = await Promise.all([
    callTenantDetail(activeTenantId).catch((): TenantDetail | null => null),
    callFindingsSummary(activeTenantId),
    callAnomalyFeed(activeTenantId, { n: 5, min_score: 0.7 }).catch(() => []),
    callCoverageMatrix(activeTenantId),
    callListModels(activeTenantId).catch((): ModelSummary[] => []),
  ]);

  const critical = summary.by_severity?.CRITICAL ?? 0;
  const high = summary.by_severity?.HIGH ?? 0;
  const anom24h = anomalyFeed.length;
  const policiesAnalysed =
    matrix.cells.length > 0
      ? new Set(matrix.cells.flatMap((c) => c.applicable_policy_ids)).size
      : 0;

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
        { label: 'Overview' },
      ]}
      actions={
        <>
          <Button variant="default" size="default" aria-label="Refresh">
            <RefreshCw size={13} strokeWidth={1.6} aria-hidden />
            Refresh
          </Button>
          <Button variant="default" size="default" aria-label="Re-run audit">
            <Play size={11} strokeWidth={1.7} aria-hidden />
            Re-run audit
          </Button>
          <Button variant="primary" size="default" aria-label="Score anomalies">
            <Play size={11} strokeWidth={1.7} aria-hidden />
            Score anomalies
          </Button>
        </>
      }
    >
      <div className="mb-5">
        <p className="eyebrow mb-1.5">
          Identity posture · {tenantDisplayName(tenants, activeTenantId)}
        </p>
        <h1 className="text-22 font-semibold tracking-[-0.012em]">Overview</h1>
        <p className="mt-1 max-w-[640px] text-13 text-fg-tertiary">
          Conditional access health, sign-in anomalies, and coverage at a glance.
        </p>
      </div>

      <div className="mb-4 grid gap-2.5 md:grid-cols-2 lg:grid-cols-4" data-testid="kpi-grid">
        <KpiCard
          label="Critical findings"
          value={critical}
          delta={critical > 0 ? `+${critical}` : 'no Δ'}
          deltaTone={critical > 0 ? 'bad' : 'neutral'}
          trend={approxTrend(critical)}
          color="var(--color-crit)"
        />
        <KpiCard
          label="High findings"
          value={high}
          delta={high > 0 ? `+${high}` : 'no Δ'}
          deltaTone={high > 0 ? 'bad' : 'neutral'}
          trend={approxTrend(high)}
          color="var(--color-high)"
        />
        <KpiCard
          label="Anomalies (24h)"
          value={anom24h}
          delta={anom24h > 0 ? `+${anom24h}` : 'no Δ'}
          deltaTone={anom24h > 0 ? 'bad' : 'neutral'}
          trend={approxTrend(anom24h)}
          color="var(--color-brand)"
        />
        <KpiCard
          label="Policies analysed"
          value={policiesAnalysed}
          footnote={`last analysed ${tenantDetail?.last_audit_at ? new Date(tenantDetail.last_audit_at).toISOString().slice(0, 10) : 'never'}`}
          color="var(--color-fg-tertiary)"
        />
      </div>

      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <div className="overflow-hidden rounded-r-md border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
            <div>
              <div className="text-13 font-semibold">Conditional access audit</div>
              <div className="mt-0.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
                {summary.total} findings · last summary {''}
                {tenantDetail?.last_audit_at ? 'recent' : 'never'}
              </div>
            </div>
            <Link
              href={`/dashboard/findings?tenant=${activeTenantId}` as never}
              className="inline-flex items-center gap-1 text-12 text-brand hover:underline"
            >
              All findings <ArrowRight size={11} aria-hidden />
            </Link>
          </div>
          <div className="p-3.5">
            <p className="eyebrow mb-2" style={{ fontSize: 10 }}>
              By severity
            </p>
            <div className="mb-4">
              <SeverityBreakdownBar bySeverity={summary.by_severity ?? {}} />
            </div>
            <p className="eyebrow mb-2" style={{ fontSize: 10 }}>
              Top categories
            </p>
            <div>
              {topCategories(summary.by_category ?? {}).map(([cat, n], i, arr) => (
                <div
                  key={cat}
                  className="flex items-center justify-between py-2"
                  style={{
                    borderBottom:
                      i === arr.length - 1 ? 'none' : '1px solid var(--color-border-subtle)',
                  }}
                >
                  <span className="text-13 capitalize">{cat}</span>
                  <span className="num text-12 text-fg-secondary">{n} findings</span>
                </div>
              ))}
              {topCategories(summary.by_category ?? {}).length === 0 && (
                <p className="text-13 text-fg-tertiary">No findings yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-r-md border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
            <div>
              <div className="text-13 font-semibold">Sign-in anomalies</div>
              <div className="mt-0.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
                {anomalyFeed.length} above threshold (70)
              </div>
            </div>
            <Link
              href={`/dashboard/anomalies?tenant=${activeTenantId}` as never}
              className="inline-flex items-center gap-1 text-12 text-brand hover:underline"
            >
              View feed <ArrowRight size={11} aria-hidden />
            </Link>
          </div>
          {anomalyFeed.length === 0 ? (
            <p className="px-3.5 py-6 text-center text-13 text-fg-tertiary">
              No anomalies above threshold.
            </p>
          ) : (
            anomalyFeed.map((score, i) => (
              <AnomalySummaryRow
                key={score.signin_id}
                score={score}
                tenantId={activeTenantId}
                isLast={i === anomalyFeed.length - 1}
              />
            ))
          )}
        </div>
      </div>

      <div className="mb-4">
        <CoverageMatrixPreview matrix={matrix} tenantId={activeTenantId} />
      </div>

      {tenantDetail && <DataFreshnessPanel tenant={tenantDetail} models={models} />}
    </AppShell>
  );
}
