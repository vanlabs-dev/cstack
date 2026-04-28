import { cn } from '@/lib/cn';

export type SeverityLevel = 'crit' | 'high' | 'med' | 'low' | 'info';

const DEFAULT_LABELS: Record<SeverityLevel, string> = {
  crit: 'Critical',
  high: 'High',
  med: 'Medium',
  low: 'Low',
  info: 'Info',
};

const ARIA_LABELS: Record<SeverityLevel, string> = {
  crit: 'Critical severity',
  high: 'High severity',
  med: 'Medium severity',
  low: 'Low severity',
  info: 'Info severity',
};

export interface SeverityBadgeProps {
  level: SeverityLevel;
  label?: string;
  className?: string;
}

export function SeverityBadge({ level, label, className }: SeverityBadgeProps) {
  return (
    <span
      role="img"
      aria-label={ARIA_LABELS[level]}
      className={cn('sev', `sev-${level}`, className)}
    >
      <span className="sev-shape" aria-hidden />
      {label ?? DEFAULT_LABELS[level]}
    </span>
  );
}

export function severityFromString(value: string | null | undefined): SeverityLevel {
  switch ((value ?? '').toUpperCase()) {
    case 'CRITICAL':
      return 'crit';
    case 'HIGH':
      return 'high';
    case 'MEDIUM':
      return 'med';
    case 'LOW':
      return 'low';
    default:
      return 'info';
  }
}
