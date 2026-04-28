import { MobileNav } from './MobileNav';
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
      <div className="hidden md:flex">
        <Sidebar tenants={tenants} activeTenantId={activeTenantId} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-none items-center gap-2 border-b border-border bg-surface pl-2 md:hidden">
          <MobileNav tenants={tenants} activeTenantId={activeTenantId} />
          <div className="min-w-0 flex-1">
            <TopBar crumbs={crumbs} actions={actions} />
          </div>
        </div>
        <div className="hidden md:block">
          <TopBar crumbs={crumbs} actions={actions} />
        </div>
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
