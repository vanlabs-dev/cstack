'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

import { cn } from '@/lib/cn';

const TABS = [
  { key: 'general', label: 'General', placeholder: false },
  { key: 'audit-rules', label: 'Audit rules', placeholder: false },
  { key: 'anomaly-tuning', label: 'Anomaly tuning', placeholder: false },
  { key: 'api-keys', label: 'API keys', placeholder: false },
  { key: 'notifications', label: 'Notifications', placeholder: true },
  { key: 'data-sync', label: 'Data & sync', placeholder: true },
  { key: 'integrations', label: 'Integrations', placeholder: true },
] as const;

export function SettingsTabs() {
  const pathname = usePathname() ?? '';
  const searchParams = useSearchParams();
  const tenant = searchParams.get('tenant');
  const tenantSuffix = tenant ? `?tenant=${tenant}` : '';

  return (
    <nav
      aria-label="Settings sections"
      className="-mx-1 mb-4 flex flex-wrap gap-x-1 gap-y-1 overflow-x-auto border-b border-border"
    >
      {TABS.map((t) => {
        const href = `/dashboard/settings/${t.key}${tenantSuffix}`;
        const active = pathname.startsWith(`/dashboard/settings/${t.key}`);
        return (
          <Link
            key={t.key}
            href={href as never}
            className={cn(
              'inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-13 transition-colors',
              active
                ? 'border-fg font-medium text-fg'
                : 'border-transparent text-fg-secondary hover:text-fg',
            )}
            aria-current={active ? 'page' : undefined}
          >
            {t.label}
            {t.placeholder && (
              <span
                className="mono rounded-r-sm bg-surface-subtle px-1 text-fg-quaternary"
                style={{ fontSize: 9, letterSpacing: '0.04em' }}
              >
                V2
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
