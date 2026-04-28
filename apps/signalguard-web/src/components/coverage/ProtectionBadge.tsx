import type { ProtectionLevel } from '@/lib/api/generated/types.gen';

const LEVEL_INFO: Record<
  ProtectionLevel,
  { label: string; bg: string; fg: string; icon: string }
> = {
  4: {
    label: 'MFA + device',
    bg: 'var(--color-cov-strong-bg)',
    fg: 'var(--color-cov-strong)',
    icon: '✓✓',
  },
  3: {
    label: 'MFA enforced',
    bg: 'var(--color-cov-good-bg)',
    fg: 'var(--color-cov-good)',
    icon: '✓',
  },
  2: {
    label: 'Device only',
    bg: 'var(--color-cov-amber-bg)',
    fg: 'var(--color-cov-amber)',
    icon: '◇',
  },
  1: {
    label: 'Report-only',
    bg: 'var(--color-cov-weak-bg)',
    fg: 'var(--color-cov-weak)',
    icon: '○',
  },
  0: {
    label: 'Unprotected',
    bg: 'var(--color-cov-bad-bg)',
    fg: 'var(--color-cov-bad)',
    icon: '×',
  },
};

interface ProtectionBadgeProps {
  level: ProtectionLevel;
  size?: 'sm' | 'lg';
}

export function ProtectionBadge({ level, size = 'sm' }: ProtectionBadgeProps) {
  const info = LEVEL_INFO[level];
  if (size === 'lg') {
    return (
      <div
        className="inline-flex items-center gap-2 rounded-r-md px-3 py-1.5"
        style={{ background: info.bg, color: info.fg }}
        role="img"
        aria-label={info.label}
      >
        <span className="mono text-18 font-semibold">{info.icon}</span>
        <span className="text-13 font-medium">{info.label}</span>
      </div>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-r-sm px-1.5 py-0.5 text-11 font-medium"
      style={{ background: info.bg, color: info.fg }}
      role="img"
      aria-label={info.label}
    >
      <span className="mono font-semibold">{info.icon}</span>
      {info.label}
    </span>
  );
}

export const COVERAGE_LEVEL_INFO = LEVEL_INFO;
