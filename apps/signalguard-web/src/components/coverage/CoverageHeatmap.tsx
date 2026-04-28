'use client';

import { useState } from 'react';

import { cn } from '@/lib/cn';

import { COVERAGE_LEVEL_INFO } from './ProtectionBadge';
import { CoverageSidePanel } from './CoverageSidePanel';

import type {
  CoverageCell,
  CoverageMatrix,
  ProtectionLevel,
} from '@/lib/api/generated/types.gen';

const USER_SEGMENTS = [
  'all_users',
  'admins_any',
  'privileged_roles',
  'guests',
  'service_accounts',
] as const;

const APP_SEGMENTS = [
  'm365_core',
  'admin_portals',
  'legacy_auth',
  'high_risk_apps',
  'all_apps',
] as const;

const USER_LABEL: Record<(typeof USER_SEGMENTS)[number], string> = {
  all_users: 'All users',
  admins_any: 'Admins',
  privileged_roles: 'Privileged roles',
  guests: 'Guests',
  service_accounts: 'Service accounts',
};

const APP_LABEL: Record<(typeof APP_SEGMENTS)[number], { label: string; hint: string }> = {
  m365_core: { label: 'M365 core', hint: 'Outlook, Teams, OneDrive' },
  admin_portals: { label: 'Admin portals', hint: 'Entra, M365 admin, Intune' },
  legacy_auth: { label: 'Legacy auth', hint: 'POP, IMAP, basic auth' },
  high_risk_apps: { label: 'High-risk apps', hint: 'Azure mgmt, key vaults' },
  all_apps: { label: 'All other apps', hint: 'Catch-all segment' },
};

interface CoverageHeatmapProps {
  matrix: CoverageMatrix;
  tenantId: string;
}

interface SelectedCell {
  cell: CoverageCell;
  userLabel: string;
  appLabel: string;
}

function cellFor(
  matrix: CoverageMatrix,
  user: string,
  app: string,
): CoverageCell | undefined {
  return matrix.cells.find((c) => c.user_segment === user && c.app_segment === app);
}

export function CoverageHeatmap({ matrix, tenantId }: CoverageHeatmapProps) {
  const [selected, setSelected] = useState<SelectedCell | null>(null);

  return (
    <>
      <div className="overflow-x-auto rounded-r-md border border-border bg-surface p-4">
        <div
          className="grid min-w-[760px] gap-1.5"
          style={{ gridTemplateColumns: '200px repeat(5, 1fr)' }}
          role="grid"
          aria-label="Coverage matrix"
        >
          <div />
          {APP_SEGMENTS.map((app) => {
            const meta = APP_LABEL[app];
            return (
              <div key={app} className="px-1 pb-2" role="columnheader">
                <p className="eyebrow text-left" style={{ fontSize: 10 }}>
                  {meta.label}
                </p>
                <p className="mono mt-0.5 text-fg-quaternary" style={{ fontSize: 10 }}>
                  {meta.hint}
                </p>
              </div>
            );
          })}
          {USER_SEGMENTS.map((user) => {
            const userLabel = USER_LABEL[user];
            return (
              <span key={user} style={{ display: 'contents' }}>
                <div
                  className="flex items-center justify-between pr-3"
                  role="rowheader"
                >
                  <span className="text-13 font-medium">{userLabel}</span>
                </div>
                {APP_SEGMENTS.map((app) => {
                  const c = cellFor(matrix, user, app);
                  const level = (c?.protection_level ?? 0) as ProtectionLevel;
                  const info = COVERAGE_LEVEL_INFO[level];
                  const isFocus =
                    selected?.cell.user_segment === user &&
                    selected?.cell.app_segment === app;
                  return (
                    <button
                      key={`${user}-${app}`}
                      type="button"
                      role="gridcell"
                      aria-label={`${userLabel} on ${APP_LABEL[app].label}, ${info.label}`}
                      onClick={() => {
                        if (c) {
                          setSelected({
                            cell: c,
                            userLabel,
                            appLabel: APP_LABEL[app].label,
                          });
                        }
                      }}
                      className={cn(
                        'flex h-16 cursor-pointer flex-col items-center justify-center gap-0.5 rounded-r-sm transition-transform',
                        isFocus
                          ? 'border-2 ring-1 ring-fg'
                          : 'border border-border-subtle hover:scale-[1.02]',
                      )}
                      style={{
                        background: info.bg,
                        color: info.fg,
                      }}
                    >
                      <span
                        className="mono"
                        style={{ fontSize: 18, fontWeight: 600 }}
                        aria-hidden
                      >
                        {info.icon}
                      </span>
                      <span
                        className="text-center"
                        style={{ fontSize: 10, opacity: 0.78 }}
                      >
                        {info.label}
                      </span>
                    </button>
                  );
                })}
              </span>
            );
          })}
        </div>
      </div>

      {selected && (
        <CoverageSidePanel
          cell={selected.cell}
          userLabel={selected.userLabel}
          appLabel={selected.appLabel}
          tenantId={tenantId}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
