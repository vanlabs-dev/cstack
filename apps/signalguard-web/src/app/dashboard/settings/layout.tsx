import { Settings } from 'lucide-react';

import { AppShell } from '@/components/layout/AppShell';
import { SettingsTabs } from '@/components/settings/SettingsTabs';
import { fetchTenantList, resolveActiveTenantId } from '@/lib/tenant';

interface SettingsLayoutProps {
  children: React.ReactNode;
}

export default async function SettingsLayout({ children }: SettingsLayoutProps) {
  const tenants = await fetchTenantList();
  const activeTenantId = await resolveActiveTenantId(undefined);
  return (
    <AppShell
      tenants={tenants}
      activeTenantId={activeTenantId}
      crumbs={[
        {
          label: 'Settings',
          pill: true,
          pillIcon: Settings,
          pillBg: 'var(--color-surface-subtle)',
          pillFg: 'var(--color-fg-secondary)',
        },
      ]}
    >
      <div className="mb-4">
        <p className="eyebrow mb-1.5">Tenant settings</p>
        <h1 className="text-22 font-semibold tracking-[-0.012em]">Settings</h1>
        <p className="mt-1 max-w-[640px] text-13 text-fg-tertiary">
          Per-tenant preferences, rules, and credentials. Some sections are placeholders until their
          backend lands.
        </p>
      </div>
      <SettingsTabs />
      {children}
    </AppShell>
  );
}
