'use client';

import {
  Activity,
  Book,
  ChevronDown,
  ChevronUp,
  Compass,
  Home,
  LineChart,
  Radar,
  Receipt,
  Settings,
  Shield,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { Avatar } from '@/components/system/Avatar';
import { StatusDot } from '@/components/system/StatusDot';
import { TenantTile } from '@/components/system/TenantTile';
import { clearApiKey } from '@/lib/api/key-storage';
import { cn } from '@/lib/cn';

import type { TenantSummary } from '@/lib/tenant';

interface SidebarProps {
  tenants: TenantSummary[];
  activeTenantId: string | null;
}

const MODULES = [
  {
    id: 'signalguard',
    icon: Shield,
    label: 'SignalGuard',
    on: true,
    href: '/dashboard/signalguard',
  },
  { id: 'license', icon: Receipt, label: 'LicenseLens', on: false },
  { id: 'drift', icon: LineChart, label: 'Driftwatch', on: false },
  { id: 'radar', icon: Radar, label: 'ChangeRadar', on: false },
  { id: 'compliance', icon: Activity, label: 'CompliancePulse', on: false },
] as const;

export function Sidebar({ tenants, activeTenantId }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [profileOpen, setProfileOpen] = useState(false);
  const [tenantOpen, setTenantOpen] = useState(false);

  const activeTenant = tenants.find((t) => t.tenant_id === activeTenantId);

  const setTenant = (id: string | null): void => {
    const next = new URLSearchParams(searchParams.toString());
    if (id) {
      next.set('tenant', id);
    } else {
      next.delete('tenant');
    }
    router.push(`${pathname}?${next.toString()}` as never);
    setTenantOpen(false);
  };

  const onClearKey = (): void => {
    clearApiKey();
    window.location.reload();
  };

  const isModuleActive = (id: string): boolean => {
    if (id === 'signalguard') {
      return Boolean(
        pathname?.startsWith('/dashboard/signalguard') ||
        pathname?.startsWith('/dashboard/findings') ||
        pathname?.startsWith('/dashboard/anomalies') ||
        pathname === '/dashboard',
      );
    }
    return false;
  };

  return (
    <aside className="flex h-full w-[224px] flex-none flex-col border-r border-border bg-surface">
      {/* Wordmark */}
      <div className="flex items-center gap-2.5 px-3.5 pt-3.5 pb-3">
        <div
          className="grid h-6 w-6 place-items-center rounded-r-md text-white"
          style={{
            background: 'linear-gradient(135deg, #1A1A19 0%, #3A3A37 100%)',
            fontFamily: 'var(--font-mono)',
            fontSize: 13,
            fontWeight: 700,
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.08)',
          }}
          aria-hidden
        >
          c
        </div>
        <div className="flex flex-col leading-[1.1]">
          <span className="text-14 font-semibold tracking-[-0.012em]">cstack</span>
          <span
            className="mono text-fg-quaternary"
            style={{ fontSize: 9.5, letterSpacing: '0.02em' }}
          >
            v0.4.2
          </span>
        </div>
        <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-fg-tertiary">
          <StatusDot kind="ok" />
          live
        </span>
      </div>

      {/* Tenant scope */}
      <div className="px-3 pt-1 pb-2.5">
        <div className="px-1 pb-1.5 text-[9.5px] font-semibold uppercase tracking-[0.07em] text-fg-tertiary">
          Tenant scope
        </div>
        <div className="relative">
          <button
            type="button"
            onClick={() => setTenantOpen((v) => !v)}
            aria-haspopup="listbox"
            aria-expanded={tenantOpen}
            className="flex w-full items-center gap-2 rounded-r border border-border bg-surface-inset px-2 py-1.5 text-left transition-colors hover:border-border-strong"
          >
            {activeTenant ? (
              <TenantTile name={activeTenant.display_name} size={18} />
            ) : (
              <span className="grid h-[18px] w-[18px] flex-none place-items-center rounded-r-sm bg-fg-quaternary text-[9.5px] font-semibold text-white">
                ALL
              </span>
            )}
            <span className="flex-1 truncate text-[12.5px] font-medium">
              {activeTenant?.display_name ?? 'All tenants'}
            </span>
            <ChevronDown size={13} className="text-fg-tertiary" />
          </button>
          {tenantOpen && (
            <div
              role="listbox"
              className="absolute left-0 right-0 top-full z-20 mt-1 max-h-[320px] overflow-y-auto rounded-r-md border border-border bg-surface py-1"
              style={{ boxShadow: 'var(--shadow-pop)' }}
            >
              <button
                type="button"
                onClick={() => setTenant(null)}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12.5px] hover:bg-surface-hover"
              >
                <span className="grid h-[18px] w-[18px] flex-none place-items-center rounded-r-sm bg-fg-quaternary text-[9.5px] font-semibold text-white">
                  ALL
                </span>
                All tenants
              </button>
              {tenants.map((t) => (
                <button
                  key={t.tenant_id}
                  type="button"
                  onClick={() => setTenant(t.tenant_id)}
                  className={cn(
                    'flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12.5px] hover:bg-surface-hover',
                    t.tenant_id === activeTenantId && 'bg-surface-subtle',
                  )}
                >
                  <TenantTile name={t.display_name} size={18} />
                  <span className="flex-1 truncate">{t.display_name}</span>
                </button>
              ))}
              {tenants.length === 0 && (
                <div className="px-3 py-2 text-12 text-fg-tertiary">No tenants registered</div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mx-3 my-1 h-px bg-border" />

      {/* Modules */}
      <div className="px-2 pt-1.5 pb-1">
        <div className="px-2 pb-1.5 text-[9.5px] font-semibold uppercase tracking-[0.07em] text-fg-tertiary">
          Modules
        </div>
        {MODULES.map((m) => {
          const active = isModuleActive(m.id);
          const Inner = (
            <div
              className={cn(
                'relative flex items-center gap-2.5 rounded-[4px] px-2 py-1.5 text-[12.5px]',
                active && 'bg-surface-subtle font-medium',
                m.on ? 'cursor-pointer text-fg' : 'cursor-default text-fg-quaternary',
              )}
            >
              {active && (
                <span
                  className="absolute -left-2 top-1.5 bottom-1.5 w-0.5 rounded-sm bg-sg"
                  aria-hidden
                />
              )}
              <span
                className={cn(
                  'grid h-5 w-5 flex-none place-items-center rounded-[4px]',
                  active ? 'bg-sg-subtle text-sg' : 'bg-transparent',
                )}
              >
                <m.icon size={13} strokeWidth={1.7} />
              </span>
              <span className="flex-1 truncate">{m.label}</span>
              {!m.on && (
                <span
                  className="mono text-fg-quaternary"
                  style={{ fontSize: 9, letterSpacing: '0.06em' }}
                >
                  SOON
                </span>
              )}
            </div>
          );
          if (m.on && 'href' in m && m.href) {
            const href =
              m.id === 'signalguard' && activeTenantId
                ? `${m.href}?tenant=${activeTenantId}`
                : m.href;
            return (
              <Link key={m.id} href={href as never} className="block my-px">
                {Inner}
              </Link>
            );
          }
          return (
            <div key={m.id} className="my-px">
              {Inner}
            </div>
          );
        })}
      </div>

      <div className="flex-1" />

      {/* Footer nav + profile */}
      <div className="border-t border-border p-2">
        {[
          { icon: Home, label: 'Home', href: '/dashboard' },
          { icon: Book, label: 'Docs', href: null },
          { icon: Settings, label: 'Settings', href: null },
        ].map((n) => {
          const inner = (
            <div className="flex items-center gap-2.5 rounded-[4px] px-2 py-1.5 text-12 text-fg-secondary hover:bg-surface-hover">
              <n.icon size={13} strokeWidth={1.6} className="text-fg-tertiary" />
              <span>{n.label}</span>
            </div>
          );
          if (n.href) {
            return (
              <Link key={n.label} href={n.href as never}>
                {inner}
              </Link>
            );
          }
          return (
            <div key={n.label} className="cursor-default opacity-60">
              {inner}
            </div>
          );
        })}

        <div className="mt-1 border-t border-border-subtle pt-2">
          <button
            type="button"
            onClick={() => setProfileOpen((v) => !v)}
            className="flex w-full items-center gap-2 rounded-[4px] px-1.5 py-1 hover:bg-surface-hover"
            aria-expanded={profileOpen}
            aria-haspopup="menu"
          >
            <Avatar name="Marcus Voss" size={24} />
            <div className="min-w-0 flex-1 text-left">
              <div className="truncate text-12 font-medium">Marcus Voss</div>
              <div className="mono text-fg-quaternary" style={{ fontSize: 10 }}>
                cstack-dev
              </div>
            </div>
            <ChevronUp size={12} className="text-fg-quaternary" />
          </button>
          {profileOpen && (
            <div
              role="menu"
              className="absolute z-30 ml-2 mt-1 w-[180px] rounded-r-md border border-border bg-surface py-1"
              style={{ boxShadow: 'var(--shadow-pop)' }}
            >
              <button
                type="button"
                role="menuitem"
                onClick={onClearKey}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-12 hover:bg-surface-hover"
              >
                <Compass size={12} strokeWidth={1.7} />
                Clear API key
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
