'use client';

import { Filter } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { Chip } from '@/components/ui/Chip';
import { cn } from '@/lib/cn';

const TIME_RANGES = [
  { key: '1h', label: '1h', hours: 1 },
  { key: '24h', label: '24h', hours: 24 },
  { key: '7d', label: '7d', hours: 24 * 7 },
  { key: '30d', label: '30d', hours: 24 * 30 },
  { key: 'all', label: 'All', hours: null as number | null },
] as const;

const SEVERITY_STEPS = [
  { key: 'all', label: 'All', score: 0 },
  { key: 'low', label: 'Low+', score: 0.7 },
  { key: 'med', label: 'Med+', score: 0.85 },
  { key: 'high', label: 'High+', score: 0.95 },
] as const;

const STATUS_OPTIONS = [
  { key: 'open', label: 'Open' },
  { key: 'dismissed', label: 'Dismissed' },
  { key: 'known-good', label: 'Known-good' },
] as const;

export function FilterRail() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const setParam = (key: string, value: string | null): void => {
    const next = new URLSearchParams(searchParams.toString());
    if (value === null) next.delete(key);
    else next.set(key, value);
    next.delete('offset');
    router.push(`${pathname}?${next.toString()}` as never);
  };

  const setTimeRange = (key: (typeof TIME_RANGES)[number]['key']): void => {
    const range = TIME_RANGES.find((r) => r.key === key);
    if (!range) return;
    const next = new URLSearchParams(searchParams.toString());
    next.set('range', key);
    if (range.hours === null) {
      next.delete('since');
    } else {
      const sinceDate = new Date(Date.now() - range.hours * 60 * 60 * 1000);
      next.set('since', sinceDate.toISOString());
    }
    next.delete('offset');
    router.push(`${pathname}?${next.toString()}` as never);
  };

  const currentRange = searchParams.get('range') ?? '7d';
  const currentMinScore = searchParams.get('min_score') ?? '0';
  const currentStatus = searchParams.get('status') ?? 'open';

  const clearAll = (): void => {
    const next = new URLSearchParams();
    const tenant = searchParams.get('tenant');
    if (tenant) next.set('tenant', tenant);
    router.push(`${pathname}?${next.toString()}` as never);
  };

  return (
    <div
      className="mb-3 flex flex-wrap items-center gap-2 rounded-r-md border border-border bg-surface px-3 py-2"
      style={{ fontSize: 12.5 }}
    >
      <Filter size={13} className="text-fg-tertiary" aria-hidden />

      <span className="eyebrow mr-1 hidden md:inline">Range</span>
      <div className="inline-flex rounded-r border border-border bg-surface-subtle p-0.5">
        {TIME_RANGES.map((r) => {
          const active = currentRange === r.key;
          return (
            <button
              key={r.key}
              type="button"
              onClick={() => setTimeRange(r.key)}
              className={cn(
                'h-[22px] rounded-r-sm px-2 transition-colors',
                active ? 'bg-surface text-fg shadow-sm' : 'text-fg-tertiary hover:text-fg',
              )}
              style={{ fontSize: 11.5, fontWeight: 500 }}
              aria-pressed={active}
            >
              {r.label}
            </button>
          );
        })}
      </div>

      <span className="eyebrow ml-2 mr-1 hidden md:inline">Min score</span>
      {SEVERITY_STEPS.map((s) => (
        <Chip
          key={s.key}
          active={currentMinScore === String(s.score)}
          onClick={() => setParam('min_score', s.score === 0 ? null : String(s.score))}
          aria-pressed={currentMinScore === String(s.score)}
        >
          {s.label}
        </Chip>
      ))}

      <span className="eyebrow ml-2 mr-1 hidden md:inline">Status</span>
      {STATUS_OPTIONS.map((s) => {
        const active = currentStatus === s.key;
        const placeholder = s.key !== 'open';
        return (
          <button
            key={s.key}
            type="button"
            disabled={placeholder}
            onClick={() => setParam('status', s.key)}
            title={placeholder ? 'Status filter lands once mutation API exists' : undefined}
            aria-pressed={active}
            className={cn(
              'inline-flex h-[22px] items-center gap-1 rounded-r-sm border px-2 text-12',
              active ? 'border-fg bg-fg text-bg' : 'border-border bg-surface text-fg-secondary',
              placeholder && 'cursor-not-allowed opacity-50',
            )}
          >
            {s.label}
          </button>
        );
      })}

      <span className="ml-auto" />
      <button
        type="button"
        onClick={clearAll}
        className="text-12 text-fg-tertiary transition-colors hover:text-fg"
      >
        Clear
      </button>
    </div>
  );
}
