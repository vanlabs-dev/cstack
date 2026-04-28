import { cn } from '@/lib/cn';

export type StatusKind = 'ok' | 'warn' | 'err' | 'idle';

const ARIA: Record<StatusKind, string> = {
  ok: 'Healthy',
  warn: 'Stale',
  err: 'Failed',
  idle: 'Idle',
};

export interface StatusDotProps {
  kind?: StatusKind;
  className?: string;
}

export function StatusDot({ kind = 'ok', className }: StatusDotProps) {
  return (
    <span role="img" aria-label={ARIA[kind]} className={cn('dot', `dot-${kind}`, className)} />
  );
}
