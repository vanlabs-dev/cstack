'use client';

import { useMemo, useState } from 'react';

import { AnomalyRow } from './AnomalyRow';
import { BulkActionsStrip } from './BulkActionsStrip';

import type { AnomalyScore } from '@/lib/api/generated/types.gen';

export interface AnomalyListSigninExtras {
  upn?: string | null;
  country?: string | null;
  city?: string | null;
  device?: string | null;
}

interface AnomalyListProps {
  scores: AnomalyScore[];
  signinExtras?: Record<string, AnomalyListSigninExtras>;
  tenantId: string;
}

export function AnomalyList({ scores, signinExtras, tenantId }: AnomalyListProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const onSelectChange = (id: string, value: boolean): void => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (value) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const onClear = (): void => setSelected(new Set());

  const toggleAll = (): void => {
    setSelected((prev) =>
      prev.size === scores.length ? new Set() : new Set(scores.map((s) => s.signin_id)),
    );
  };

  const allSelected = useMemo(
    () => scores.length > 0 && selected.size === scores.length,
    [scores, selected],
  );

  if (scores.length === 0) {
    return (
      <div className="rounded-r-md border border-border bg-surface px-6 py-12 text-center">
        <p className="mb-1 text-13 text-fg">No anomalies match the current filters</p>
        <p className="text-12 text-fg-tertiary">
          Score new signins via the action button or relax the filters above.
        </p>
      </div>
    );
  }

  return (
    <div>
      <BulkActionsStrip count={selected.size} onClear={onClear} />
      <div className="overflow-hidden rounded-r-md border border-border bg-surface">
        <div
          className="grid items-center gap-2.5 border-b border-border bg-surface px-3.5 py-2 text-fg-tertiary"
          style={{
            gridTemplateColumns:
              '32px minmax(0, 1.4fr) 90px minmax(0, 1.1fr) minmax(0, 1fr) minmax(0, 1.6fr) 64px',
            fontSize: 11.5,
            fontWeight: 500,
            letterSpacing: '0.02em',
          }}
        >
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            aria-label="Select all"
            className="h-3.5 w-3.5 cursor-pointer accent-brand"
          />
          <span>User</span>
          <span>Time</span>
          <span>Location</span>
          <span className="hidden md:inline">Device</span>
          <span>Top features</span>
          <span className="text-right">Score</span>
        </div>
        {scores.map((score) => (
          <AnomalyRow
            key={score.signin_id}
            score={score}
            signin={signinExtras?.[score.signin_id]}
            tenantId={tenantId}
            selected={selected.has(score.signin_id)}
            onSelectChange={onSelectChange}
          />
        ))}
      </div>
    </div>
  );
}
