'use client';

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { FormRow } from '@/components/settings/FormRow';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/cn';

import type { TenantSummary } from '@/lib/tenant';

const DEFAULT_TENANT_KEY = 'cstack-default-tenant';
const DENSITY_KEY = 'cstack-density';

interface GeneralFormProps {
  tenants: TenantSummary[];
  activeTenantId: string | null;
}

type Density = 'compact' | 'comfortable';

function applyDensity(density: Density): void {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.density = density;
}

export function GeneralForm({ tenants, activeTenantId }: GeneralFormProps) {
  const { theme, setTheme } = useTheme();
  const [defaultTenant, setDefaultTenant] = useState<string>('');
  const [density, setDensity] = useState<Density>('compact');
  const [saved, setSaved] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setDefaultTenant(window.localStorage.getItem(DEFAULT_TENANT_KEY) ?? '');
    const persisted = (window.localStorage.getItem(DENSITY_KEY) as Density | null) ?? 'compact';
    setDensity(persisted);
    applyDensity(persisted);
  }, []);

  const onSave = (): void => {
    if (typeof window === 'undefined') return;
    if (defaultTenant) {
      window.localStorage.setItem(DEFAULT_TENANT_KEY, defaultTenant);
    } else {
      window.localStorage.removeItem(DEFAULT_TENANT_KEY);
    }
    window.localStorage.setItem(DENSITY_KEY, density);
    applyDensity(density);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1500);
  };

  const tenant = tenants.find((t) => t.tenant_id === activeTenantId);

  return (
    <div className="rounded-r-md border border-border bg-surface px-4 py-1">
      <FormRow
        label="Tenant display name"
        description="Editing requires the live Graph tenant API; read-only for now."
      >
        <Input value={tenant?.display_name ?? '—'} readOnly />
      </FormRow>

      <FormRow
        label="Default tenant on app load"
        description="Locally persisted preference. Pick the tenant the dashboard should land on."
      >
        <select
          value={defaultTenant}
          onChange={(event) => setDefaultTenant(event.target.value)}
          className="h-8 w-full rounded-r border border-border bg-surface-inset px-2 text-13 text-fg outline-none focus:border-brand"
        >
          <option value="">No default — pick on each load</option>
          {tenants.map((t) => (
            <option key={t.tenant_id} value={t.tenant_id}>
              {t.display_name}
            </option>
          ))}
        </select>
      </FormRow>

      <FormRow
        label="Theme"
        description="Light is the design's first-class theme; dark is a polish target."
      >
        <div className="inline-flex rounded-r border border-border bg-surface-subtle p-0.5">
          {(['light', 'dark', 'system'] as const).map((t) => {
            const active = (theme ?? 'light') === t;
            return (
              <button
                key={t}
                type="button"
                onClick={() => setTheme(t)}
                className={cn(
                  'h-[24px] rounded-r-sm px-3 capitalize transition-colors',
                  active ? 'bg-surface text-fg shadow-sm' : 'text-fg-tertiary hover:text-fg',
                )}
                style={{ fontSize: 12, fontWeight: 500 }}
                aria-pressed={active}
              >
                {t}
              </button>
            );
          })}
        </div>
      </FormRow>

      <FormRow
        label="Density"
        description="Compact is the engineer-grade default; Comfortable adds 25% to row paddings."
      >
        <div className="inline-flex rounded-r border border-border bg-surface-subtle p-0.5">
          {(['compact', 'comfortable'] as const).map((d) => {
            const active = density === d;
            return (
              <button
                key={d}
                type="button"
                onClick={() => setDensity(d)}
                className={cn(
                  'h-[24px] rounded-r-sm px-3 capitalize transition-colors',
                  active ? 'bg-surface text-fg shadow-sm' : 'text-fg-tertiary hover:text-fg',
                )}
                style={{ fontSize: 12, fontWeight: 500 }}
                aria-pressed={active}
              >
                {d}
              </button>
            );
          })}
        </div>
      </FormRow>

      <div className="flex items-center gap-3 py-4">
        <Button variant="primary" onClick={onSave}>
          Save preferences
        </Button>
        {saved && <span className="text-12 text-ok">Saved.</span>}
      </div>
    </div>
  );
}
