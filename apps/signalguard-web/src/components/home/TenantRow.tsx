import Link from 'next/link';

import { StatusDot, type StatusKind } from '@/components/system/StatusDot';
import { TenantTile } from '@/components/system/TenantTile';
import { formatRelativeTime, shortTenantId } from '@/lib/format';

import type { TenantSummary } from '@/lib/tenant';

interface TenantRowProps {
  tenant: TenantSummary;
}

function syncStatus(t: TenantSummary): { kind: StatusKind; label: string } {
  if (!t.last_extract_at) return { kind: 'idle', label: 'Never synced' };
  const ageHours = (Date.now() - new Date(t.last_extract_at).getTime()) / 1000 / 60 / 60;
  if (ageHours < 1) return { kind: 'ok', label: 'Synced' };
  if (ageHours < 24) return { kind: 'ok', label: 'Synced' };
  return { kind: 'warn', label: 'Stale' };
}

export function TenantRow({ tenant }: TenantRowProps) {
  const status = syncStatus(tenant);
  const tenantHref = `/dashboard/findings?tenant=${tenant.tenant_id}`;
  return (
    <tr className="transition-colors duration-[var(--duration-fast)] hover:bg-surface-hover">
      <td className="px-2.5 py-2.5">
        <Link href={tenantHref as never} className="flex items-center gap-2 outline-none">
          <TenantTile name={tenant.display_name} size={18} />
          <div>
            <div className="text-13 font-medium">{tenant.display_name}</div>
            <div className="mono text-fg-quaternary" style={{ fontSize: 10.5 }}>
              {shortTenantId(tenant.tenant_id)}
            </div>
          </div>
        </Link>
      </td>
      <td className="num px-2.5 py-2.5 text-right text-13 text-fg-secondary">—</td>
      <td className="px-2.5 py-2.5">
        <span className="inline-flex items-center gap-1.5 text-12">
          <StatusDot kind={status.kind} />
          {status.label}
        </span>
      </td>
      <td className="mono px-2.5 py-2.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
        {formatRelativeTime(tenant.last_extract_at)}
      </td>
    </tr>
  );
}
