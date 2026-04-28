'use client';

import { Bookmark, ChevronDown, ChevronRight, MoreHorizontal } from 'lucide-react';
import { useState } from 'react';

import { SeverityBadge, severityFromString } from '@/components/system/SeverityBadge';
import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';

import type { Finding } from '@/lib/api/generated/types.gen';

import { ExpandedFinding } from './ExpandedFinding';

interface FindingsTableProps {
  findings: Finding[];
}

function affectedDescription(f: Finding): string {
  const objs = f.affected_objects ?? [];
  if (objs.length === 0) return f.rule_id;
  if (objs.length === 1) {
    const o = objs[0]!;
    return `${o.type}: ${o.display_name}`;
  }
  return `${objs.length} affected · ${objs[0]?.type ?? ''}`;
}

export function FindingsTable({ findings }: FindingsTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (findings.length === 0) {
    return (
      <div className="rounded-r-md border border-border bg-surface px-6 py-12 text-center">
        <p className="mb-1 text-13 text-fg">No findings above the current filter</p>
        <p className="text-12 text-fg-tertiary">
          Re-run the audit to refresh, or clear filters to widen the view.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-r-md border border-border bg-surface">
      <table className="w-full border-separate border-spacing-0 text-13">
        <thead>
          <tr>
            <Th className="w-8" />
            <Th className="w-[100px]">Severity</Th>
            <Th>Finding</Th>
            <Th className="hidden w-[200px] lg:table-cell">ID</Th>
            <Th className="hidden w-[70px] md:table-cell">Age</Th>
            <Th className="w-[24px]" />
          </tr>
        </thead>
        <tbody>
          {findings.map((f) => {
            const expanded = expandedId === f.id;
            const sev = severityFromString(f.severity);
            return (
              <FindingRowFragment
                key={f.id}
                finding={f}
                expanded={expanded}
                onToggle={() => setExpandedId(expanded ? null : f.id)}
                sev={sev}
                affected={affectedDescription(f)}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children, className }: { children?: React.ReactNode; className?: string }) {
  return (
    <th
      className={cn(
        'border-b border-border bg-surface px-2.5 py-2 text-left text-fg-tertiary',
        className,
      )}
      style={{ fontSize: 11.5, fontWeight: 500, letterSpacing: '0.02em' }}
    >
      {children}
    </th>
  );
}

interface FindingRowProps {
  finding: Finding;
  expanded: boolean;
  onToggle: () => void;
  sev: ReturnType<typeof severityFromString>;
  affected: string;
}

function FindingRowFragment({ finding, expanded, onToggle, sev, affected }: FindingRowProps) {
  return (
    <>
      <tr
        className={cn(
          'cursor-pointer transition-colors duration-[var(--duration-fast)] hover:bg-surface-hover',
          expanded && 'bg-surface-subtle hover:bg-surface-subtle',
        )}
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <td className="px-2.5 py-2.5 align-middle">
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onToggle();
            }}
            className="grid h-5 w-5 place-items-center rounded-r-sm text-fg-tertiary hover:bg-surface-hover"
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? (
              <ChevronDown size={12} aria-hidden />
            ) : (
              <ChevronRight size={12} aria-hidden />
            )}
          </button>
        </td>
        <td className="px-2.5 py-2.5 align-middle">
          <SeverityBadge level={sev} />
        </td>
        <td className="px-2.5 py-2.5 align-middle">
          <div>
            <div className="text-13 font-medium leading-[1.35]">{finding.title}</div>
            <div className="mono mt-0.5 text-11 text-fg-tertiary">{affected}</div>
          </div>
        </td>
        <td className="mono hidden px-2.5 py-2.5 align-middle text-11 text-fg-tertiary lg:table-cell">
          {finding.id.slice(0, 16)}
        </td>
        <td
          className="mono hidden px-2.5 py-2.5 align-middle text-fg-tertiary md:table-cell"
          style={{ fontSize: 11.5 }}
        >
          {formatRelativeTime(finding.first_seen_at)}
        </td>
        <td className="px-2.5 py-2.5 align-middle">
          <div className="flex items-center gap-1 text-fg-quaternary">
            {finding.category === 'rule' && (
              <Bookmark size={11} className="opacity-0" aria-hidden />
            )}
            <MoreHorizontal size={14} aria-hidden />
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td
            colSpan={6}
            className="border-b border-border p-0"
            style={{ background: 'var(--color-surface-subtle)' }}
          >
            <ExpandedFinding finding={finding} />
          </td>
        </tr>
      )}
    </>
  );
}
