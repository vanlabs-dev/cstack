import { Download, RefreshCw, Shield } from 'lucide-react';

import { CoverageHeatmap } from '@/components/coverage/CoverageHeatmap';
import { CoverageLegend } from '@/components/coverage/CoverageLegend';
import { CoverageToolbar } from '@/components/coverage/CoverageToolbar';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/Button';
import { callCoverageMatrix } from '@/lib/api/calls';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

import type { TenantSummary } from '@/lib/tenant';

interface CoveragePageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

function tenantDisplayName(tenants: TenantSummary[], id: string): string {
  return tenants.find((t) => t.tenant_id === id)?.display_name ?? id;
}

export default async function CoverageMatrixPage({ searchParams }: CoveragePageProps) {
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
          { label: 'Coverage matrix' },
        ]}
      >
        <p className="text-13 text-fg-tertiary">No tenant selected.</p>
      </AppShell>
    );
  }

  const matrix = await callCoverageMatrix(activeTenantId);
  const policyCount = new Set(matrix.cells.flatMap((c) => c.applicable_policy_ids)).size;

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
        { label: 'Coverage matrix' },
      ]}
      actions={
        <>
          <Button variant="default" size="default" aria-label="Export">
            <Download size={12} aria-hidden />
            Export
          </Button>
          <Button variant="default" size="default" aria-label="Recompute">
            <RefreshCw size={12} aria-hidden />
            Recompute
          </Button>
        </>
      }
    >
      <div className="mb-4">
        <p className="eyebrow mb-1.5">
          Identity posture · {tenantDisplayName(tenants, activeTenantId)}
        </p>
        <h1 className="text-22 font-semibold tracking-[-0.012em]">Coverage matrix</h1>
        <p className="mt-1 max-w-[640px] text-13 text-fg-tertiary">
          Protection level for each user × app segment. Each cell shows the strongest control that
          consistently applies. {policyCount} polic{policyCount === 1 ? 'y' : 'ies'} analysed.
        </p>
      </div>

      <CoverageToolbar />

      <div className="mb-3">
        <CoverageHeatmap matrix={matrix} tenantId={activeTenantId} />
      </div>

      <div className="overflow-hidden rounded-r-md border border-border bg-surface">
        <CoverageLegend />
      </div>
    </AppShell>
  );
}
