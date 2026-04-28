import { Sidebar } from './Sidebar';
import { TopBar, type Crumb } from './TopBar';

import type { TenantSummary } from '@/lib/tenant';

export interface AppShellProps {
  tenants: TenantSummary[];
  activeTenantId: string | null;
  crumbs: Crumb[];
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function AppShell({ tenants, activeTenantId, crumbs, actions, children }: AppShellProps) {
  return (
    <div className="flex h-screen w-full bg-bg">
      <Sidebar tenants={tenants} activeTenantId={activeTenantId} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar crumbs={crumbs} actions={actions} />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
