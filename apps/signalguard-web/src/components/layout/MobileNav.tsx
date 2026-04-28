'use client';

import { Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Sidebar } from './Sidebar';

import type { TenantSummary } from '@/lib/tenant';

interface MobileNavProps {
  tenants: TenantSummary[];
  activeTenantId: string | null;
}

export function MobileNav({ tenants, activeTenantId }: MobileNavProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open navigation"
        className="grid h-8 w-8 place-items-center rounded-r-sm text-fg-secondary hover:bg-surface-hover md:hidden"
      >
        <Menu size={16} aria-hidden />
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-fg/15 md:hidden"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            className="fixed inset-y-0 left-0 z-50 flex md:hidden"
            role="dialog"
            aria-label="Navigation"
          >
            <Sidebar tenants={tenants} activeTenantId={activeTenantId} />
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close navigation"
              className="absolute right-2 top-3 grid h-7 w-7 place-items-center rounded-r-sm bg-surface text-fg-tertiary hover:bg-surface-hover"
            >
              <X size={14} aria-hidden />
            </button>
          </div>
        </>
      )}
    </>
  );
}
