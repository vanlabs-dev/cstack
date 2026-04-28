import { Clock, RefreshCw } from 'lucide-react';

import { CopyButton } from '@/components/findings/CopyButton';
import { StatusDot } from '@/components/system/StatusDot';
import { Button } from '@/components/ui/Button';
import { formatRelativeTime } from '@/lib/format';

import type { ModelSummary, TenantDetail } from '@/lib/api/generated/types.gen';

interface DataFreshnessPanelProps {
  tenant: TenantDetail;
  models: ModelSummary[];
}

export function DataFreshnessPanel({ tenant, models }: DataFreshnessPanelProps) {
  const lastSync = tenant.last_extract_at;
  const champion = models.find((m) => m.current_champion_version !== null);
  const modelDescriptor = champion
    ? `${champion.name}:v${champion.current_champion_version}`
    : 'no model registered';
  const lastTrained = champion?.last_trained_at ?? null;
  return (
    <div className="rounded-r-md border border-border bg-surface">
      <div
        className="flex flex-wrap items-center gap-x-6 gap-y-2 px-3.5 py-3"
        style={{ fontSize: 12.5 }}
      >
        <span className="flex items-center gap-2">
          <StatusDot kind={lastSync ? 'ok' : 'idle'} />
          <span className="text-fg-tertiary">Last sync</span>
          <span className="mono text-fg">{formatRelativeTime(lastSync)}</span>
        </span>
        <span className="hidden h-3.5 w-px bg-border md:inline-block" aria-hidden />
        <span className="flex items-center gap-2">
          <Clock size={13} className="text-fg-tertiary" aria-hidden />
          <span className="text-fg-tertiary">Next sync</span>
          <span className="mono">manual</span>
        </span>
        <span className="hidden h-3.5 w-px bg-border md:inline-block" aria-hidden />
        <span className="flex items-center gap-2">
          <span className="text-fg-tertiary">Mode</span>
          <span className="mono">fixture</span>
        </span>
        <span className="ml-auto">
          <Button variant="ghost" size="sm">
            <RefreshCw size={11} aria-hidden />
            Refresh now
          </Button>
        </span>
      </div>
      <div
        className="flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-border-subtle px-3.5 py-2 text-fg-tertiary"
        style={{ fontSize: 11.5 }}
      >
        <span className="flex items-center gap-1.5">
          <span>Tenant</span>
          <span className="mono text-fg">{tenant.tenant_id}</span>
          <CopyButton text={tenant.tenant_id} label="Copy" className="h-5 px-1.5" />
        </span>
        <span className="flex items-center gap-1.5">
          <span>Model</span>
          <span className="mono text-fg">{modelDescriptor}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span>Last trained</span>
          <span className="mono text-fg">{formatRelativeTime(lastTrained)}</span>
        </span>
      </div>
    </div>
  );
}
