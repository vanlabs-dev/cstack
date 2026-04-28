import { ChevronRight, type LucideIcon } from 'lucide-react';

import { cn } from '@/lib/cn';

export interface Crumb {
  label: string;
  pill?: boolean;
  pillBg?: string;
  pillFg?: string;
  pillIcon?: LucideIcon;
}

export interface TopBarProps {
  crumbs: Crumb[];
  actions?: React.ReactNode;
}

export function TopBar({ crumbs, actions }: TopBarProps) {
  return (
    <header className="flex h-11 flex-none items-center gap-3 border-b border-border bg-surface px-3.5">
      <div className="flex min-w-0 flex-1 items-center gap-2 text-13">
        {crumbs.map((c, i) => (
          <span key={`${c.label}-${i}`} className="flex items-center gap-2">
            {i > 0 && <ChevronRight size={11} className="text-fg-quaternary" aria-hidden />}
            <span
              className={cn(
                'inline-flex items-center gap-1.5',
                i === crumbs.length - 1 ? 'font-medium text-fg' : 'text-fg-secondary',
              )}
            >
              {c.pill ? (
                <span
                  className="inline-flex items-center gap-1 rounded-r-sm px-1.5 py-0.5 text-11 font-medium"
                  style={{
                    background: c.pillBg ?? 'var(--color-sg-subtle)',
                    color: c.pillFg ?? 'var(--color-sg-text)',
                  }}
                >
                  {c.pillIcon ? <c.pillIcon size={11} strokeWidth={1.8} /> : null}
                  {c.label}
                </span>
              ) : (
                <span className="truncate">{c.label}</span>
              )}
            </span>
          </span>
        ))}
      </div>
      {actions && <div className="flex items-center gap-1.5">{actions}</div>}
    </header>
  );
}
