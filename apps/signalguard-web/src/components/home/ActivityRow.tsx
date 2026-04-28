import Link from 'next/link';

import { SeverityBadge, severityFromString } from '@/components/system/SeverityBadge';
import { formatRelativeTime } from '@/lib/format';

import type { ActivityEntry } from '@/lib/activity';

interface ActivityRowProps {
  entry: ActivityEntry;
  isLast: boolean;
}

function rowHref(entry: ActivityEntry): string {
  const f = entry.finding;
  const tenant = entry.tenant.tenant_id;
  if (f.category === 'anomaly') {
    const signinId = (f.evidence?.signin_id as string | undefined) ?? '';
    if (signinId) {
      return `/dashboard/anomalies/${encodeURIComponent(signinId)}?tenant=${tenant}`;
    }
  }
  return `/dashboard/findings?tenant=${tenant}&rule_id=${encodeURIComponent(f.rule_id)}`;
}

export function ActivityRow({ entry, isLast }: ActivityRowProps) {
  const f = entry.finding;
  const sev = severityFromString(f.severity);
  return (
    <Link
      href={rowHref(entry) as never}
      className="grid items-center gap-2.5 px-3.5 py-2.5 transition-colors hover:bg-surface-hover"
      style={{
        gridTemplateColumns: '82px minmax(0, 1fr) auto',
        borderBottom: isLast ? 'none' : '1px solid var(--color-border-subtle)',
      }}
    >
      <SeverityBadge level={sev} />
      <div className="min-w-0">
        <div className="truncate text-13 leading-[1.35]">{f.title}</div>
        <div className="mt-0.5 flex gap-2 text-fg-tertiary" style={{ fontSize: 11.5 }}>
          <span>{entry.tenant.display_name}</span>
          <span className="text-fg-quaternary">·</span>
          <span className="mono">{f.rule_id}</span>
        </div>
      </div>
      <span className="mono whitespace-nowrap text-fg-quaternary" style={{ fontSize: 11 }}>
        {formatRelativeTime(f.first_seen_at)}
      </span>
    </Link>
  );
}
