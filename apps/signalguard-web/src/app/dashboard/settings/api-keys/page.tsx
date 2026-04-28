import { ApiKeysPanel } from '@/components/settings/ApiKeysPanel';
import { callListApiKeys } from '@/lib/api/calls';
import { resolveActiveTenantId } from '@/lib/tenant';

interface PageProps {
  searchParams: Promise<{ tenant?: string | string[] }>;
}

export default async function ApiKeysPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const tenantParam = Array.isArray(params.tenant) ? params.tenant[0] : params.tenant;
  const activeTenantId = await resolveActiveTenantId(tenantParam);
  if (!activeTenantId) {
    return (
      <div className="rounded-r-md border border-border bg-surface px-4 py-6 text-13 text-fg-tertiary">
        No tenant in scope. Pick a tenant in the sidebar to manage its keys.
      </div>
    );
  }
  const keys = await callListApiKeys(activeTenantId).catch(() => []);
  return <ApiKeysPanel tenantId={activeTenantId} initialKeys={keys} />;
}
