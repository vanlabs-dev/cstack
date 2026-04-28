import { KpiSparkline } from '@/components/system/Sparkline';
import { cn } from '@/lib/cn';

export interface KpiCardProps {
  label: string;
  value: number;
  delta?: string;
  deltaTone?: 'good' | 'bad' | 'neutral';
  trend?: number[];
  color?: string;
  footnote?: string;
}

export function KpiCard({
  label,
  value,
  delta,
  deltaTone = 'neutral',
  trend,
  color = 'var(--color-brand)',
  footnote,
}: KpiCardProps) {
  const deltaColor =
    deltaTone === 'good' ? 'text-ok' : deltaTone === 'bad' ? 'text-crit' : 'text-fg-quaternary';
  return (
    <div className="rounded-r-md border border-border bg-surface p-3.5 md:p-4">
      <div className="mb-2 text-fg-tertiary" style={{ fontSize: 11.5, letterSpacing: '0.01em' }}>
        {label}
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="min-w-0">
          <div
            className="num leading-none tracking-[-0.02em]"
            style={{ fontSize: 28, fontWeight: 600 }}
          >
            {value.toLocaleString()}
          </div>
          {delta && (
            <div className={cn('mono mt-1 text-11', deltaColor)}>
              {delta} <span className="text-fg-quaternary">14d</span>
            </div>
          )}
          {!delta && footnote && (
            <div className="mono mt-1 text-11 text-fg-tertiary">{footnote}</div>
          )}
        </div>
        {trend && trend.length >= 2 && (
          <div className="w-[120px] flex-none md:w-[100px]">
            <KpiSparkline data={trend} color={color} />
          </div>
        )}
      </div>
    </div>
  );
}
