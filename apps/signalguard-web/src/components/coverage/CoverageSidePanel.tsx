'use client';

import { ExternalLink, X } from 'lucide-react';
import Link from 'next/link';
import { useEffect } from 'react';

import { Button } from '@/components/ui/Button';

import { ProtectionBadge } from './ProtectionBadge';

import type { CoverageCell, ProtectionLevel } from '@/lib/api/generated/types.gen';

interface CoverageSidePanelProps {
  cell: CoverageCell;
  userLabel: string;
  appLabel: string;
  tenantId: string;
  onClose: () => void;
}

function whatsMissing(cell: CoverageCell): string[] {
  const level = cell.protection_level as ProtectionLevel;
  if (level === 4) return ['Already at strongest level: MFA plus compliant device.'];
  const items: string[] = [];
  if (level < 3) items.push('No policy enforces MFA for this segment.');
  if (level < 2) items.push('No compliant-device requirement for this segment.');
  if (level === 1) items.push('Coverage is report-only; no enforcement.');
  if (cell.app_segment === 'legacy_auth' && level < 4) {
    items.push('Legacy auth client app types are not blocked.');
  }
  if (cell.applicable_policy_ids.length === 0) {
    items.push('No conditional access policy targets this combination.');
  }
  return items;
}

export function CoverageSidePanel({
  cell,
  userLabel,
  appLabel,
  tenantId,
  onClose,
}: CoverageSidePanelProps) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const level = cell.protection_level as ProtectionLevel;
  const missing = whatsMissing(cell);

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-fg/10"
        onClick={onClose}
        aria-hidden
        data-testid="coverage-panel-backdrop"
      />
      <aside
        className="fixed inset-x-0 bottom-0 z-50 max-h-[70vh] overflow-y-auto rounded-t-md border border-b-0 border-border bg-surface md:inset-y-0 md:right-0 md:left-auto md:max-h-none md:w-[360px] md:rounded-r-md md:rounded-tr-none md:border-b md:border-l md:border-l-border md:border-r-0"
        style={{ boxShadow: 'var(--shadow-modal)' }}
        role="dialog"
        aria-label={`${userLabel} on ${appLabel}`}
      >
        <header className="flex items-start justify-between border-b border-border-subtle px-4 py-3.5">
          <div>
            <p className="eyebrow mb-1" style={{ fontSize: 10 }}>
              Cell · {userLabel} × {appLabel}
            </p>
            <ProtectionBadge level={level} size="lg" />
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="grid h-7 w-7 place-items-center rounded-r-sm text-fg-tertiary hover:bg-surface-hover"
          >
            <X size={14} aria-hidden />
          </button>
        </header>

        <section className="border-b border-border-subtle px-4 py-3.5">
          <p className="eyebrow mb-2" style={{ fontSize: 10 }}>
            Applicable policies ({cell.applicable_policy_ids.length})
          </p>
          {cell.applicable_policy_ids.length === 0 ? (
            <p className="text-12 text-fg-tertiary">
              No conditional access policy targets this combination.
            </p>
          ) : (
            <ul className="space-y-1.5 text-12">
              {cell.applicable_policy_ids.map((id) => (
                <li key={id} className="flex items-center gap-2">
                  <Link
                    href={
                      `/dashboard/findings?tenant=${tenantId}&category=rule` as never
                    }
                    className="mono truncate text-fg hover:text-brand"
                  >
                    {id}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="border-b border-border-subtle px-4 py-3.5">
          <p className="eyebrow mb-2" style={{ fontSize: 10 }}>
            What&apos;s missing
          </p>
          {missing.length === 0 ? (
            <p className="text-12 text-fg-tertiary">
              Detail pending in coverage explainer V2.
            </p>
          ) : (
            <ul className="space-y-1.5 pl-4 text-12 leading-[1.6]">
              {missing.map((m) => (
                <li key={m} className="list-disc">
                  {m}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="px-4 py-3.5">
          <p className="eyebrow mb-2" style={{ fontSize: 10 }}>
            Recommended actions
          </p>
          <div className="space-y-1.5">
            <a
              href="https://entra.microsoft.com/#view/Microsoft_AAD_ConditionalAccess/PoliciesMenuBlade/~/Policies"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-r border border-brand bg-brand px-3 py-1.5 text-13 font-medium text-white transition-colors hover:bg-brand-hover"
            >
              Create policy
              <ExternalLink size={12} aria-hidden />
            </a>
            <Link
              href={`/dashboard/findings?tenant=${tenantId}` as never}
              className="block w-full"
            >
              <Button variant="default" className="w-full justify-center">
                Run audit on this segment
              </Button>
            </Link>
            <p className="text-11 text-fg-tertiary">
              {cell.member_count.toLocaleString()} member{cell.member_count === 1 ? '' : 's'} in
              segment.
            </p>
          </div>
        </section>
      </aside>
    </>
  );
}
