'use client';

import { Filter, X } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { Chip } from '@/components/ui/Chip';
import { cn } from '@/lib/cn';

type Severity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
type Category = 'coverage' | 'rule' | 'exclusion' | 'anomaly';

const SEVERITY_OPTIONS: Severity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const CATEGORY_OPTIONS: Category[] = ['coverage', 'rule', 'exclusion', 'anomaly'];

export function FilterChipStrip() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const minSeverity = searchParams.get('min_severity') ?? null;
  const categoriesParam = searchParams.getAll('category');

  const setParam = (key: string, value: string | null): void => {
    const next = new URLSearchParams(searchParams.toString());
    if (value === null) next.delete(key);
    else next.set(key, value);
    next.delete('offset');
    router.push(`${pathname}?${next.toString()}` as never);
  };

  const toggleCategory = (cat: Category): void => {
    const current = new Set(categoriesParam);
    if (current.has(cat)) current.delete(cat);
    else current.add(cat);
    const next = new URLSearchParams(searchParams.toString());
    next.delete('category');
    for (const c of current) next.append('category', c);
    next.delete('offset');
    router.push(`${pathname}?${next.toString()}` as never);
  };

  const clearAll = (): void => {
    const next = new URLSearchParams();
    const tenant = searchParams.get('tenant');
    if (tenant) next.set('tenant', tenant);
    router.push(`${pathname}?${next.toString()}` as never);
  };

  const hasFilters = minSeverity !== null || categoriesParam.length > 0;

  return (
    <div className="mb-2.5 flex flex-wrap items-center gap-1.5 rounded-r-md border border-border bg-surface px-2.5 py-2">
      <Filter size={13} className="text-fg-tertiary" aria-hidden />
      <span className="eyebrow mr-1">Severity</span>
      {SEVERITY_OPTIONS.map((s) => (
        <Chip
          key={s}
          active={minSeverity === s}
          onClick={() => setParam('min_severity', minSeverity === s ? null : s)}
          aria-pressed={minSeverity === s}
        >
          ≥ {s.toLowerCase()}
          {minSeverity === s && <X size={10} aria-hidden />}
        </Chip>
      ))}
      <span className="eyebrow ml-2 mr-1">Category</span>
      {CATEGORY_OPTIONS.map((c) => {
        const active = categoriesParam.includes(c);
        return (
          <Chip key={c} active={active} onClick={() => toggleCategory(c)} aria-pressed={active}>
            {c}
            {active && <X size={10} aria-hidden />}
          </Chip>
        );
      })}
      <span className={cn('flex-1', hasFilters && 'min-w-[12px]')} />
      {hasFilters && (
        <button
          type="button"
          onClick={clearAll}
          className="text-12 text-fg-tertiary transition-colors hover:text-fg"
        >
          Clear
        </button>
      )}
    </div>
  );
}
