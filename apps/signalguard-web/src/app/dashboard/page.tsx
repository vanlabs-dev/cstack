import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

import { AppShell } from '@/components/layout/AppShell';

interface DashboardPageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const params = await searchParams;
  const tenantParam = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;

  let tenants: Awaited<ReturnType<typeof fetchTenantList>> = [];
  let activeTenantId: string | null = null;
  try {
    tenants = await fetchTenantList();
    activeTenantId = await resolveActiveTenantId(tenantParam);
  } catch (err) {
    console.error('home: tenant fetch failed', err);
  }

  return (
    <AppShell tenants={tenants} activeTenantId={activeTenantId} crumbs={[{ label: 'Home' }]}>
      <div className="p-12 text-center text-fg-tertiary">
        <p className="text-22 text-fg">Phase 3 shell ready</p>
        <p className="mt-2 text-13">Tenants loaded: {tenants.length}</p>
      </div>
    </AppShell>
  );
}
