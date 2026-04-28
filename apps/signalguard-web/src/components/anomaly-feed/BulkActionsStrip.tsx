'use client';

import { AlertTriangle, Check, Trash2, X } from 'lucide-react';

import { Button } from '@/components/ui/Button';

interface BulkActionsStripProps {
  count: number;
  onClear: () => void;
}

export function BulkActionsStrip({ count, onClear }: BulkActionsStripProps) {
  if (count === 0) return null;
  return (
    <div
      className="mb-2.5 flex flex-wrap items-center gap-2 rounded-r-md border border-brand bg-brand-subtle px-3 py-2"
      role="region"
      aria-label="Bulk actions"
    >
      <span className="text-13 font-medium text-brand-text">Selected: {count}</span>
      <span className="h-3.5 w-px bg-border-strong" aria-hidden />
      <Button
        variant="ghost"
        size="sm"
        title="Dismiss flow lands once mutation API exists"
        aria-label="Dismiss selected"
      >
        <Trash2 size={11} aria-hidden />
        Dismiss
      </Button>
      <Button
        variant="ghost"
        size="sm"
        title="Mark known-good lands once mutation API exists"
        aria-label="Mark known-good"
      >
        <Check size={11} aria-hidden />
        Mark known-good
      </Button>
      <Button
        variant="ghost"
        size="sm"
        title="Escalate flow lands once mutation API exists"
        aria-label="Escalate selected"
      >
        <AlertTriangle size={11} aria-hidden />
        Escalate
      </Button>
      <span className="ml-auto" />
      <Button variant="ghost" size="sm" onClick={onClear} aria-label="Clear selection">
        <X size={11} aria-hidden />
        Clear
      </Button>
    </div>
  );
}
