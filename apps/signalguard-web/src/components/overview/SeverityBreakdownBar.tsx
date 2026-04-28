import { SeverityBadge, type SeverityLevel } from '@/components/system/SeverityBadge';

const ROWS: Array<{ key: string; level: SeverityLevel; color: string }> = [
  { key: 'CRITICAL', level: 'crit', color: 'var(--color-crit)' },
  { key: 'HIGH', level: 'high', color: 'var(--color-high)' },
  { key: 'MEDIUM', level: 'med', color: 'var(--color-med)' },
  { key: 'LOW', level: 'low', color: 'var(--color-low)' },
  { key: 'INFO', level: 'info', color: 'var(--color-info)' },
];

interface SeverityBreakdownBarProps {
  bySeverity: Record<string, number>;
}

export function SeverityBreakdownBar({ bySeverity }: SeverityBreakdownBarProps) {
  const max = Math.max(1, ...Object.values(bySeverity));
  return (
    <div className="flex flex-col gap-1.5">
      {ROWS.map(({ key, level, color }) => {
        const n = bySeverity[key] ?? 0;
        const widthPct = (n / max) * 100;
        return (
          <div
            key={key}
            className="grid items-center gap-2.5"
            style={{ gridTemplateColumns: '90px 1fr 32px' }}
          >
            <SeverityBadge level={level} />
            <div className="h-1.5 overflow-hidden rounded-sm bg-surface-subtle">
              <div
                className="h-full"
                style={{ width: `${widthPct}%`, background: color, opacity: 0.85 }}
              />
            </div>
            <span
              className="num text-right"
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: n === 0 ? 'var(--color-fg-quaternary)' : 'var(--color-fg)',
              }}
            >
              {n}
            </span>
          </div>
        );
      })}
    </div>
  );
}
