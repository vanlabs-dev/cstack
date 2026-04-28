'use client';

import { Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { callDeleteApiKey } from '@/lib/api/calls';
import { formatRelativeTime } from '@/lib/format';

import { CreateApiKeyDialog } from './CreateApiKeyDialog';

import type { ApiKeySummary } from '@/lib/api/generated/types.gen';

interface ApiKeysPanelProps {
  tenantId: string;
  initialKeys: ApiKeySummary[];
}

export function ApiKeysPanel({ tenantId, initialKeys }: ApiKeysPanelProps) {
  const [keys, setKeys] = useState<ApiKeySummary[]>(initialKeys);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  const onCreated = async (): Promise<void> => {
    try {
      const response = await fetch(`/dashboard/settings/api-keys/refresh`, {
        cache: 'no-store',
      });
      if (response.ok) {
        const fresh: ApiKeySummary[] = await response.json();
        setKeys(fresh);
      }
    } catch {
      window.location.reload();
    }
  };

  const onRevoke = async (label: string): Promise<void> => {
    setRevokeError(null);
    try {
      await callDeleteApiKey(tenantId, label);
      setKeys((prev) => prev.filter((k) => k.label !== label));
    } catch (err) {
      setRevokeError(err instanceof Error ? err.message : 'Revoke failed');
    }
  };

  return (
    <>
      <div className="overflow-hidden rounded-r-md border border-border bg-surface">
        <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
          <div>
            <div className="text-13 font-semibold">API keys</div>
            <div className="mt-0.5 text-fg-tertiary" style={{ fontSize: 11.5 }}>
              {keys.length} key{keys.length === 1 ? '' : 's'} for this tenant. Hashes are stored in
              tenants.json; plaintext is shown once at create time.
            </div>
          </div>
          <Button
            variant="primary"
            size="default"
            onClick={() => setDialogOpen(true)}
            aria-label="Create API key"
          >
            <Plus size={11} aria-hidden />
            Create key
          </Button>
        </div>
        {keys.length === 0 ? (
          <p className="px-3.5 py-6 text-center text-13 text-fg-tertiary">
            No API keys yet. Create one to authorise the dashboard or a CI script.
          </p>
        ) : (
          <table className="w-full border-separate border-spacing-0 text-13">
            <thead>
              <tr>
                <th
                  className="border-b border-border bg-surface px-3.5 py-2 text-left text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500 }}
                >
                  Label
                </th>
                <th
                  className="border-b border-border bg-surface px-3.5 py-2 text-left text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500 }}
                >
                  Created
                </th>
                <th
                  className="border-b border-border bg-surface px-3.5 py-2 text-left text-fg-tertiary"
                  style={{ fontSize: 11.5, fontWeight: 500 }}
                >
                  Last used
                </th>
                <th className="w-[40px] border-b border-border bg-surface" />
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.label} data-testid="api-key-row">
                  <td className="border-b border-border-subtle px-3.5 py-2.5 last:border-b-0">
                    <span className="text-13 font-medium">{k.label}</span>
                  </td>
                  <td className="mono border-b border-border-subtle px-3.5 py-2.5 text-fg-secondary last:border-b-0">
                    {formatRelativeTime(k.created_at)}
                  </td>
                  <td className="border-b border-border-subtle px-3.5 py-2.5 text-fg-quaternary last:border-b-0">
                    N/A (no usage telemetry)
                  </td>
                  <td className="border-b border-border-subtle px-3.5 py-2.5 last:border-b-0">
                    <button
                      type="button"
                      onClick={() => onRevoke(k.label)}
                      aria-label={`Revoke ${k.label}`}
                      className="grid h-6 w-6 place-items-center rounded-r-sm text-fg-tertiary hover:bg-surface-hover hover:text-crit"
                    >
                      <Trash2 size={12} aria-hidden />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {revokeError && (
          <p className="px-3.5 pb-3 text-12 text-crit">Revoke failed: {revokeError}</p>
        )}
      </div>
      <CreateApiKeyDialog
        tenantId={tenantId}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={onCreated}
      />
    </>
  );
}
