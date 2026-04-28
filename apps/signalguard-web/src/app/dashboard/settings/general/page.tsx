import { GeneralForm } from '@/components/settings/GeneralForm';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

interface GeneralPageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

export default async function GeneralSettingsPage({ searchParams }: GeneralPageProps) {
  const params = await searchParams;
  const tenantParam = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;
  const tenants = await fetchTenantList();
  const activeTenantId = await resolveActiveTenantId(tenantParam);
  return <GeneralForm tenants={tenants} activeTenantId={activeTenantId} />;
}
