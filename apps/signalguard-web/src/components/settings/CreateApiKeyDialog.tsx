'use client';

import { Check, Copy, X } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { callCreateApiKey } from '@/lib/api/calls';

interface CreateApiKeyDialogProps {
  tenantId: string;
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateApiKeyDialog({
  tenantId,
  open,
  onClose,
  onCreated,
}: CreateApiKeyDialogProps) {
  const [label, setLabel] = useState('default');
  const [submitting, setSubmitting] = useState(false);
  const [plaintext, setPlaintext] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  const reset = (): void => {
    setLabel('default');
    setPlaintext(null);
    setError(null);
    setCopied(false);
  };

  const onSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await callCreateApiKey(tenantId, { label });
      setPlaintext(response.key);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to mint key');
    } finally {
      setSubmitting(false);
    }
  };

  const onCopy = async (): Promise<void> => {
    if (!plaintext) return;
    try {
      await navigator.clipboard.writeText(plaintext);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard not available; user can select and copy manually.
    }
  };

  const close = (): void => {
    reset();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-fg/15 px-4">
      <div
        className="w-full max-w-[440px] rounded-r-md border border-border bg-surface p-5"
        style={{ boxShadow: 'var(--shadow-modal)' }}
        role="dialog"
        aria-label="Create API key"
      >
        <header className="mb-3 flex items-start justify-between">
          <div>
            <h2 className="text-16 font-semibold">Create API key</h2>
            <p className="mt-0.5 text-12 text-fg-tertiary">
              Plaintext is shown once. Save it somewhere safe.
            </p>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Close"
            className="grid h-7 w-7 place-items-center rounded-r-sm text-fg-tertiary hover:bg-surface-hover"
          >
            <X size={14} aria-hidden />
          </button>
        </header>

        {plaintext ? (
          <div>
            <label className="eyebrow mb-1.5 block">New key</label>
            <div className="mb-3 flex items-stretch gap-1">
              <Input
                readOnly
                value={plaintext}
                onFocus={(event) => event.currentTarget.select()}
                className="font-mono"
              />
              <Button
                variant="default"
                size="lg"
                onClick={onCopy}
                aria-label={copied ? 'Copied' : 'Copy'}
              >
                {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
            <p className="mb-3 text-12 text-crit">
              This plaintext key will not be shown again. Close the dialog only after copying.
            </p>
            <div className="flex justify-end">
              <Button variant="primary" onClick={close}>
                Done
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={onSubmit}>
            <label htmlFor="api-key-label" className="eyebrow mb-1.5 block">
              Label
            </label>
            <Input
              id="api-key-label"
              required
              autoFocus
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="dashboard"
            />
            {error && <p className="mt-2 text-12 text-crit">{error}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={close} type="button">
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={!label.trim() || submitting}>
                {submitting ? 'Minting…' : 'Create key'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
