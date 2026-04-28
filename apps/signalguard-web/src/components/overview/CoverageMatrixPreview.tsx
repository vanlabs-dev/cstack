import Link from 'next/link';

import type { CoverageMatrix, ProtectionLevel } from '@/lib/api/generated/types.gen';

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
  privileged_roles: 'Privileged',
  guests: 'Guests',
  service_accounts: 'Service',
};
const APP_LABEL: Record<(typeof APP_SEGMENTS)[number], string> = {
  m365_core: 'M365',
  admin_portals: 'Admin',
  legacy_auth: 'Legacy',
  high_risk_apps: 'High-risk',
  all_apps: 'All apps',
};

const LEVEL_STYLE: Record<ProtectionLevel, { bg: string; fg: string; icon: string }> = {
  4: { bg: 'var(--color-cov-strong-bg)', fg: 'var(--color-cov-strong)', icon: '✓✓' },
  3: { bg: 'var(--color-cov-good-bg)', fg: 'var(--color-cov-good)', icon: '✓' },
  2: { bg: 'var(--color-cov-amber-bg)', fg: 'var(--color-cov-amber)', icon: '◇' },
  1: { bg: 'var(--color-cov-weak-bg)', fg: 'var(--color-cov-weak)', icon: '○' },
  0: { bg: 'var(--color-cov-bad-bg)', fg: 'var(--color-cov-bad)', icon: '×' },
};

interface CoverageMatrixPreviewProps {
  matrix: CoverageMatrix;
  tenantId: string;
}

function levelFor(matrix: CoverageMatrix, user: string, app: string): ProtectionLevel {
  const cell = matrix.cells.find((c) => c.user_segment === user && c.app_segment === app);
  return (cell?.protection_level ?? 0) as ProtectionLevel;
}

export function CoverageMatrixPreview({ matrix, tenantId }: CoverageMatrixPreviewProps) {
  return (
    <div className="overflow-hidden rounded-r-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
        <div>
          <div className="text-13 font-semibold">Coverage</div>
          <div className="mt-0.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
            Protection level by user × app segment
          </div>
        </div>
        <Link
          href={`/dashboard/signalguard/coverage?tenant=${tenantId}` as never}
          className="text-12 text-brand hover:underline"
        >
          View full matrix →
        </Link>
      </div>
      <div className="overflow-x-auto p-3.5">
        <div
          className="grid min-w-[560px] gap-1"
          style={{ gridTemplateColumns: '110px repeat(5, 1fr)' }}
        >
          <div />
          {APP_SEGMENTS.map((app) => (
            <div key={app} className="eyebrow text-center" style={{ fontSize: 10 }}>
              {APP_LABEL[app]}
            </div>
          ))}
          {USER_SEGMENTS.map((user) => (
            <span key={user} style={{ display: 'contents' }}>
              <div
                className="flex items-center text-12 text-fg-secondary"
                style={{ paddingRight: 8 }}
              >
                {USER_LABEL[user]}
              </div>
              {APP_SEGMENTS.map((app) => {
                const level = levelFor(matrix, user, app);
                const style = LEVEL_STYLE[level];
                return (
                  <Link
                    key={`${user}-${app}`}
                    href={
                      `/dashboard/signalguard/coverage?tenant=${tenantId}&user=${user}&app=${app}` as never
                    }
                    aria-label={`${USER_LABEL[user]} on ${APP_LABEL[app]}, level ${level}`}
                    className="grid h-9 place-items-center rounded-r-sm border border-border-subtle"
                    style={{
                      background: style.bg,
                      color: style.fg,
                    }}
                  >
                    <span className="mono" style={{ fontSize: 12, fontWeight: 600 }}>
                      {style.icon}
                    </span>
                  </Link>
                );
              })}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
