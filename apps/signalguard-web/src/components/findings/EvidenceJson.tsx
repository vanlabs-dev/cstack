'use client';

import { useState } from 'react';

import { CopyButton } from './CopyButton';

interface EvidenceJsonProps {
  evidence: Record<string, unknown>;
}

function isComplex(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object' && value !== null) return Object.keys(value).length > 0;
  return false;
}

function renderScalar(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

function shortPreview(value: unknown): string {
  if (Array.isArray(value)) return `[${value.length} items]`;
  if (typeof value === 'object' && value !== null) {
    const keys = Object.keys(value);
    return `{${keys.length} fields}`;
  }
  return renderScalar(value);
}

export function EvidenceJson({ evidence }: EvidenceJsonProps) {
  const entries = Object.entries(evidence);
  if (entries.length === 0) {
    return <p className="text-13 text-fg-tertiary">No evidence captured.</p>;
  }
  return (
    <div className="overflow-hidden rounded-r border border-border bg-surface">
      {entries.map(([key, value], i) => (
        <EvidenceRow key={key} name={key} value={value} isLast={i === entries.length - 1} />
      ))}
    </div>
  );
}

interface EvidenceRowProps {
  name: string;
  value: unknown;
  isLast: boolean;
}

function EvidenceRow({ name, value, isLast }: EvidenceRowProps) {
  const [open, setOpen] = useState(false);
  const complex = isComplex(value);
  const looksId =
    typeof value === 'string' &&
    (/^[0-9a-f-]{8,}$/i.test(value) ||
      /^\d+\.\d+\.\d+\.\d+$/.test(value) ||
      /^[A-F0-9]{40}$/.test(value));
  return (
    <div
      className="grid items-start gap-3 px-3 py-2 text-12"
      style={{
        gridTemplateColumns: '180px 1fr auto',
        borderBottom: isLast ? 'none' : '1px dashed var(--color-border-subtle)',
      }}
    >
      <span className="mono text-fg-tertiary">{name}</span>
      <div className="min-w-0">
        {complex ? (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-12 text-brand-text underline-offset-2 hover:underline"
          >
            {open ? '(collapse)' : shortPreview(value)}
          </button>
        ) : (
          <span className={looksId ? 'mono break-all text-fg' : 'break-words text-fg'}>
            {renderScalar(value)}
          </span>
        )}
        {complex && open && (
          <pre className="mono mt-1 max-h-[240px] overflow-auto rounded-r border border-border-subtle bg-surface-inset p-2 text-11 text-fg">
            {JSON.stringify(value, null, 2)}
          </pre>
        )}
      </div>
      <CopyButton
        text={
          typeof value === 'string' || typeof value === 'number'
            ? String(value)
            : JSON.stringify(value)
        }
        label="Copy"
      />
    </div>
  );
}
