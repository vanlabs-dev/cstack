import { AnomalyTuningForm } from '@/components/settings/AnomalyTuningForm';
import { callListModels } from '@/lib/api/calls';
import { resolveActiveTenantId } from '@/lib/tenant';

interface PageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

export default async function AnomalyTuningPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const tenantParam = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;
  const activeTenantId = await resolveActiveTenantId(tenantParam);
  const models = activeTenantId ? await callListModels(activeTenantId).catch(() => []) : [];
  return <AnomalyTuningForm models={models} />;
}
