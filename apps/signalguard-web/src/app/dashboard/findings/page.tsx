import { Download, Play, Shield } from 'lucide-react';

import { FilterChipStrip } from '@/components/findings/FilterChipStrip';
import { FindingsTable } from '@/components/findings/FindingsTable';
import { Pagination } from '@/components/findings/Pagination';
import { RightRail } from '@/components/findings/RightRail';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/Button';
import { callFindingsSummary, callListFindings } from '@/lib/api/calls';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

import type { TenantSummary } from '@/lib/tenant';

interface FindingsPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

const ALLOWED_SEVERITIES = new Set(['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
const ALLOWED_CATEGORIES = new Set(['coverage', 'rule', 'exclusion', 'anomaly']);

function pickFirst(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function pickAll(value: string | string[] | undefined): string[] {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function tenantDisplayName(tenants: TenantSummary[], id: string): string {
  return tenants.find((t) => t.tenant_id === id)?.display_name ?? id;
}

export default async function FindingsPage({ searchParams }: FindingsPageProps) {
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
          { label: 'Findings' },
        ]}
      >
        <div className="rounded-r-md border border-border bg-surface px-6 py-12 text-center">
          <p className="text-13 text-fg-tertiary">
            No tenant in scope. Pick a tenant in the sidebar to load findings.
          </p>
        </div>
      </AppShell>
    );
  }

  const minSeverityRaw = pickFirst(params.min_severity);
  const minSeverity =
    minSeverityRaw && ALLOWED_SEVERITIES.has(minSeverityRaw)
      ? (minSeverityRaw as 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL')
      : undefined;
  const categories = pickAll(params.category).filter((c) => ALLOWED_CATEGORIES.has(c)) as Array<
    'coverage' | 'rule' | 'exclusion' | 'anomaly'
  >;
  const ruleId = pickFirst(params.rule_id);
  const limit = Math.min(Math.max(parseInt(pickFirst(params.limit) ?? '25', 10) || 25, 1), 100);
  const offset = Math.max(parseInt(pickFirst(params.offset) ?? '0', 10) || 0, 0);

  const [page, summary] = await Promise.all([
    callListFindings({
      tenantId: activeTenantId,
      minSeverity,
      category: categories.length > 0 ? categories : undefined,
      ruleId,
      limit,
      offset,
    }),
    callFindingsSummary(activeTenantId),
  ]);

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
        { label: 'CA audit' },
        { label: 'Findings' },
      ]}
      actions={
        <>
          <Button variant="default" size="default">
            <Download size={12} strokeWidth={1.6} aria-hidden />
            Export
          </Button>
          <Button variant="primary" size="default">
            <Play size={11} strokeWidth={1.7} aria-hidden />
            Re-run audit
          </Button>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_240px]">
        <div>
          <header className="mb-4 flex items-end justify-between gap-4">
            <div>
              <p className="eyebrow mb-1.5">Conditional access · {summary.total} findings</p>
              <h1 className="text-22 font-semibold tracking-[-0.012em]">Findings</h1>
              <p className="mt-1 max-w-[640px] text-13 text-fg-tertiary">
                {page.total} of {summary.total} open findings shown. Triage to keep the queue near
                zero.
              </p>
            </div>
          </header>

          <FilterChipStrip />

          <FindingsTable findings={page.items} />

          <Pagination total={page.total} limit={limit} offset={offset} hasMore={page.has_more} />
        </div>

        <RightRail summary={summary} filteredTotal={page.total} />
      </div>
    </AppShell>
  );
}
