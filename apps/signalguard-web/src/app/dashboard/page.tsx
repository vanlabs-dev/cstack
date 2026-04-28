import { Activity, LineChart, Plus, Radar, Receipt, RefreshCw, Shield } from 'lucide-react';

import { ActivityRow } from '@/components/home/ActivityRow';
import { ModuleCard, type ModuleCardData } from '@/components/home/ModuleCard';
import { TenantRow } from '@/components/home/TenantRow';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/ui/Button';
import { fetchRecentActivity, totalsFromActivity } from '@/lib/activity';
import { formatRelativeTime, timeOfDay } from '@/lib/format';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

interface HomePageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

const TIME_OF_DAY_LABEL: Record<ReturnType<typeof timeOfDay>, string> = {
  morning: 'Good morning',
  afternoon: 'Good afternoon',
  evening: 'Good evening',
};

function buildModules(activeTenantCount: number, openFindings: number): ModuleCardData[] {
  return [
    {
      id: 'sg',
      name: 'SignalGuard',
      desc: 'Identity posture, conditional access audit, sign-in anomalies.',
      icon: Shield,
      accent: 'var(--color-sg)',
      accentBg: 'var(--color-sg-subtle)',
      status: 'active',
      findings: openFindings,
      tenants: activeTenantCount,
    },
    {
      id: 'll',
      name: 'LicenseLens',
      desc: 'Per-tenant license utilisation, reclamation, SKU drift.',
      icon: Receipt,
      accent: '#7C3AED',
      accentBg: '#F1ECFB',
      status: 'soon',
      eta: 'Q3 2026',
    },
    {
      id: 'dw',
      name: 'Driftwatch',
      desc: 'Configuration drift across Exchange, SharePoint, Intune baselines.',
      icon: LineChart,
      accent: '#0E7490',
      accentBg: '#E0F2F4',
      status: 'soon',
      eta: 'Q4 2026',
    },
    {
      id: 'cr',
      name: 'ChangeRadar',
      desc: 'Audit-log diffing across tenants. Surface what changed, by whom, when.',
      icon: Radar,
      accent: '#9F1239',
      accentBg: '#FBE7EC',
      status: 'soon',
      eta: 'Q4 2026',
    },
    {
      id: 'cp',
      name: 'CompliancePulse',
      desc: 'CIS, NCSC, Essential 8 control mapping with evidence collection.',
      icon: Activity,
      accent: '#A16207',
      accentBg: '#FAF1DD',
      status: 'soon',
      eta: '2027',
    },
  ];
}

export default async function DashboardPage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const tenantParam = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;

  const tenants = await fetchTenantList();
  const activeTenantId = await resolveActiveTenantId(tenantParam);

  const activity = await fetchRecentActivity(tenants);
  const totals = totalsFromActivity(activity);
  const lastRefreshed = tenants
    .map((t) => t.last_extract_at)
    .filter((v): v is string => Boolean(v))
    .sort()
    .pop();
  const greeting = TIME_OF_DAY_LABEL[timeOfDay()];
  const modules = buildModules(tenants.length, activity.length);

  return (
    <AppShell
      tenants={tenants}
      activeTenantId={activeTenantId}
      crumbs={[{ label: 'Home' }]}
      actions={
        <>
          <Button variant="default" size="default">
            <RefreshCw size={13} strokeWidth={1.6} aria-hidden />
            Sync all
          </Button>
          <Button variant="primary" size="default">
            <Plus size={13} strokeWidth={1.7} aria-hidden />
            Add tenant
          </Button>
        </>
      }
    >
      {/* Header strip */}
      <div className="mb-6">
        <p className="eyebrow mb-2">Workspace · cstack-dev</p>
        <div className="flex flex-wrap items-baseline gap-3.5">
          <h1 className="text-22 font-semibold tracking-[-0.018em]">{greeting}</h1>
          <span className="text-13 text-fg-tertiary">
            {tenants.length} tenants connected ·{' '}
            <span
              style={{
                color: totals.critical > 0 ? 'var(--color-crit)' : undefined,
                fontWeight: totals.critical > 0 ? 500 : undefined,
              }}
            >
              {totals.open} open findings
            </span>{' '}
            · last refreshed <span className="mono">{formatRelativeTime(lastRefreshed)}</span>
          </span>
        </div>
      </div>

      {/* Module grid */}
      <section className="mb-6">
        <div className="mb-2.5 flex items-center justify-between">
          <h2 className="text-13 font-semibold">Modules</h2>
          <span className="mono text-fg-tertiary" style={{ fontSize: 11.5 }}>
            {modules.filter((m) => m.status === 'active').length} / {modules.length} active
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2.5 md:grid-cols-5">
          {modules.map((m) => (
            <ModuleCard key={m.id} module={m} />
          ))}
        </div>
      </section>

      {/* Two columns */}
      <section className="grid gap-4 md:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        {/* Tenants */}
        <div className="overflow-hidden rounded-r-md border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
            <div>
              <div className="text-13 font-semibold">Connected tenants</div>
              <div className="mt-0.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
                Microsoft Graph · {tenants.length} connected
              </div>
            </div>
            <Button variant="default" size="sm">
              <Plus size={11} aria-hidden />
              Add
            </Button>
          </div>
          <table className="w-full border-separate border-spacing-0 text-13">
            <thead>
              <tr>
                <th
                  className="border-b border-border bg-surface px-2.5 py-2 text-left text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500, letterSpacing: '0.02em' }}
                >
                  Tenant
                </th>
                <th
                  className="w-[90px] border-b border-border bg-surface px-2.5 py-2 text-right text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500, letterSpacing: '0.02em' }}
                >
                  Users
                </th>
                <th
                  className="w-[110px] border-b border-border bg-surface px-2.5 py-2 text-left text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500, letterSpacing: '0.02em' }}
                >
                  Sync
                </th>
                <th
                  className="w-[110px] border-b border-border bg-surface px-2.5 py-2 text-left text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500, letterSpacing: '0.02em' }}
                >
                  Last refresh
                </th>
              </tr>
            </thead>
            <tbody>
              {tenants.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-3.5 py-6 text-center text-fg-tertiary">
                    No tenants registered. Run{' '}
                    <code className="mono text-fg">cstack fixtures load-all</code>.
                  </td>
                </tr>
              ) : (
                tenants.map((t) => <TenantRow key={t.tenant_id} tenant={t} />)
              )}
            </tbody>
          </table>
        </div>

        {/* Activity */}
        <div className="overflow-hidden rounded-r-md border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
            <div>
              <div className="text-13 font-semibold">Recent activity</div>
              <div className="mt-0.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
                Cross-tenant · last 24 hours
              </div>
            </div>
            <Button variant="ghost" size="sm" aria-label="Refresh activity">
              <RefreshCw size={11} aria-hidden />
            </Button>
          </div>
          {activity.length === 0 ? (
            <div className="px-3.5 py-6 text-center text-fg-tertiary">
              No findings yet. Run{' '}
              <code className="mono text-fg">cstack audit all --tenant tenant-b</code>.
            </div>
          ) : (
            activity.map((entry, i) => (
              <ActivityRow
                key={`${entry.tenant.tenant_id}-${entry.finding.id}`}
                entry={entry}
                isLast={i === activity.length - 1}
              />
            ))
          )}
        </div>
      </section>
    </AppShell>
  );
}
