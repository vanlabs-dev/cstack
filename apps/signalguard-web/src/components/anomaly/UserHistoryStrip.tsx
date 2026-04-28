'use client';

import Link from 'next/link';

import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';

import type { SignIn } from '@/lib/api/generated/types.gen';

interface UserHistoryStripProps {
  signins: SignIn[];
  tenantId: string;
  highlightId: string;
}

export function UserHistoryStrip({ signins, tenantId, highlightId }: UserHistoryStripProps) {
  if (signins.length === 0) {
    return (
      <div className="overflow-hidden rounded-r-md border border-border bg-surface">
        <div className="border-b border-border px-3.5 py-3 text-13 font-semibold">
          Recent sign-ins
        </div>
        <div className="px-3.5 py-6 text-13 text-fg-tertiary">No prior sign-ins for this user.</div>
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-r-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
        <div>
          <div className="text-13 font-semibold">Recent sign-ins</div>
          <div className="mt-0.5 text-11 text-fg-tertiary">Last {signins.length} sessions</div>
        </div>
      </div>
      <div className="flex items-end gap-[2px] overflow-x-auto px-3.5 pt-3.5 pb-2 h-[78px]">
        {signins.map((s) => {
          const flagged = s.riskState === 'atRisk' || s.riskLevelDuringSignIn === 'high';
          const isCurrent = s.id === highlightId;
          const heightPct = flagged ? 90 : isCurrent ? 90 : 35;
          return (
            <Link
              key={s.id}
              href={`/dashboard/anomalies/${encodeURIComponent(s.id)}?tenant=${tenantId}` as never}
              className={cn(
                'relative w-1 flex-none rounded-sm transition-opacity hover:opacity-100',
                isCurrent && 'ring-1 ring-brand',
              )}
              style={{
                height: `${heightPct}%`,
                background: flagged ? 'var(--color-crit)' : 'var(--color-border-strong)',
                opacity: flagged ? 0.9 : 0.6,
              }}
              title={`${formatRelativeTime(s.createdDateTime)} · ${s.location?.countryOrRegion ?? '?'}`}
              aria-label={`Sign-in at ${s.createdDateTime}`}
            />
          );
        })}
      </div>
      <div className="flex justify-between border-t border-border-subtle px-3.5 py-2 text-10 text-fg-quaternary">
        <span className="mono">
          {formatRelativeTime(signins[signins.length - 1]?.createdDateTime)}
        </span>
        <span className="mono">{formatRelativeTime(signins[0]?.createdDateTime)}</span>
      </div>
    </div>
  );
}
