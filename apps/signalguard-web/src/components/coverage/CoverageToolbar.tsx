'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { cn } from '@/lib/cn';

const TOGGLES = [
  {
    key: 'include_disabled',
    label: 'Include disabled policies',
  },
  {
    key: 'report_only_protective',
    label: 'Treat report-only as protection',
  },
] as const;

export function CoverageToolbar() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const toggle = (key: string): void => {
    const next = new URLSearchParams(searchParams.toString());
    const current = searchParams.get(key) === '1';
    if (current) next.delete(key);
    else next.set(key, '1');
    router.push(`${pathname}?${next.toString()}` as never);
  };

  return (
    <div
      className="mb-3 flex flex-wrap items-center gap-3 rounded-r-md border border-border bg-surface px-3 py-2"
      style={{ fontSize: 12.5 }}
    >
      {TOGGLES.map((t) => {
        const on = searchParams.get(t.key) === '1';
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => toggle(t.key)}
            className="inline-flex items-center gap-2 rounded-r-sm px-1 py-0.5"
            aria-pressed={on}
          >
            <span
              className={cn(
                'relative inline-block h-3.5 w-6 rounded-full transition-colors',
                on ? 'bg-brand' : 'bg-border-strong',
              )}
              aria-hidden
            >
              <span
                className="absolute top-[1px] h-3 w-3 rounded-full bg-white shadow-sm transition-[left]"
                style={{ left: on ? 11 : 1 }}
              />
            </span>
            {t.label}
          </button>
        );
      })}
      <span className="hidden h-3.5 w-px bg-border md:inline-block" aria-hidden />
      <span
        className="mono ml-auto text-fg-tertiary"
        style={{ fontSize: 11 }}
      >
        Live recompute on each request
      </span>
    </div>
  );
}
