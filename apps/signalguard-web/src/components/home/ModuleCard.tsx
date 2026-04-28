import { ArrowRight, type LucideIcon } from 'lucide-react';

import { StatusDot } from '@/components/system/StatusDot';

export interface ActiveModule {
  id: string;
  name: string;
  desc: string;
  icon: LucideIcon;
  accent: string;
  accentBg: string;
  status: 'active';
  findings: number;
  tenants: number;
}

export interface SoonModule {
  id: string;
  name: string;
  desc: string;
  icon: LucideIcon;
  accent: string;
  accentBg: string;
  status: 'soon';
  eta: string;
}

export type ModuleCardData = ActiveModule | SoonModule;

interface ModuleCardProps {
  module: ModuleCardData;
}

export function ModuleCard({ module }: ModuleCardProps) {
  const Icon = module.icon;
  const isActive = module.status === 'active';
  return (
    <div
      className="relative rounded-r-md border bg-surface p-3.5 transition-colors duration-[var(--duration-base)] ease-[var(--ease-cs)]"
      style={{
        opacity: isActive ? 1 : 0.7,
        cursor: isActive ? 'pointer' : 'default',
        borderColor: isActive ? 'var(--color-border-strong)' : 'var(--color-border)',
      }}
    >
      <div className="mb-4 flex items-center justify-between">
        <span
          className="grid h-7 w-7 place-items-center rounded-r-md"
          style={{
            background: module.accentBg,
            color: module.accent,
            filter: isActive ? 'none' : 'saturate(0.4)',
          }}
        >
          <Icon size={15} strokeWidth={1.7} />
        </span>
        {isActive ? (
          <span className="inline-flex items-center gap-1.5 text-11 text-fg-tertiary">
            <StatusDot kind="ok" />
            Active
          </span>
        ) : (
          <span
            className="mono text-fg-quaternary uppercase"
            style={{ fontSize: 10, letterSpacing: '0.04em' }}
          >
            In development
          </span>
        )}
      </div>
      <div className="mb-1 text-14 font-semibold tracking-[-0.005em]">{module.name}</div>
      <div className="min-h-[52px] text-12 leading-[1.45] text-fg-tertiary">{module.desc}</div>
      <div className="mt-3 flex items-center justify-between border-t border-border-subtle pt-2.5">
        {module.status === 'active' ? (
          <>
            <span className="mono text-fg-secondary" style={{ fontSize: 11.5 }}>
              {module.findings} findings · {module.tenants} tenants
            </span>
            <ArrowRight size={12} className="text-fg-tertiary" />
          </>
        ) : (
          <span className="mono text-fg-quaternary" style={{ fontSize: 11 }}>
            ETA {module.eta}
          </span>
        )}
      </div>
    </div>
  );
}
