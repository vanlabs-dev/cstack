import { SeverityBadge, type SeverityLevel } from '@/components/system/SeverityBadge';

import type { FindingsSummary } from '@/lib/api/generated/types.gen';

interface RightRailProps {
  summary: FindingsSummary;
  filteredTotal: number;
}

const SEVERITY_ORDER: { key: string; level: SeverityLevel }[] = [
  { key: 'CRITICAL', level: 'crit' },
  { key: 'HIGH', level: 'high' },
  { key: 'MEDIUM', level: 'med' },
  { key: 'LOW', level: 'low' },
  { key: 'INFO', level: 'info' },
];

export function RightRail({ summary, filteredTotal }: RightRailProps) {
  const total = summary.total ?? 0;
  return (
    <aside className="flex flex-col gap-2.5">
      <div className="rounded-r-md border border-border bg-surface p-3">
        <p className="eyebrow mb-2.5">Filtered total</p>
        <div
          className="num text-28 font-semibold leading-none tracking-[-0.02em]"
          aria-label="Filtered findings count"
        >
          {filteredTotal}
        </div>
        <div className="mono mt-1 text-11 text-fg-tertiary">of {total} open</div>
      </div>
      <div className="rounded-r-md border border-border bg-surface p-3">
        <p className="eyebrow mb-2">Severity breakdown</p>
        {SEVERITY_ORDER.map(({ key, level }) => {
          const count = summary.by_severity?.[key] ?? 0;
          return (
            <div
              key={key}
              className="flex items-center justify-between border-b border-border-subtle py-1.5 last:border-b-0"
            >
              <SeverityBadge level={level} />
              <span
                className="num text-12"
                style={{
                  color: count === 0 ? 'var(--color-fg-quaternary)' : 'var(--color-fg)',
                }}
              >
                {count}
              </span>
            </div>
          );
        })}
      </div>
      <div className="rounded-r-md border border-border bg-surface p-3">
        <p className="eyebrow mb-2">Bulk actions</p>
        <p className="mb-2 text-11 text-fg-tertiary">Snooze & resolve land in 5b</p>
        {['Snooze with reason', 'Mark resolved', 'Export selection'].map((label) => (
          <button
            key={label}
            disabled
            className="mb-0.5 block w-full cursor-not-allowed rounded-r-sm px-2 py-1 text-left text-12 text-fg-quaternary opacity-60"
          >
            {label}
          </button>
        ))}
      </div>
      <div className="rounded-r-md border border-border bg-surface p-3">
        <p className="eyebrow mb-2">Shortcuts</p>
        <div className="space-y-1.5 text-12 text-fg-secondary">
          {[
            ['Next finding', 'J'],
            ['Expand row', 'Enter'],
            ['Snooze', 'S'],
            ['Resolve', 'R'],
          ].map(([label, key]) => (
            <div key={label} className="flex justify-between">
              <span>{label}</span>
              <span className="kbd">{key}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
