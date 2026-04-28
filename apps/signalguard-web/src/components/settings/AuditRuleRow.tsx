'use client';

import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { useState } from 'react';

import { SeverityBadge, severityFromString } from '@/components/system/SeverityBadge';
import { cn } from '@/lib/cn';

export interface AuditRuleData {
  id: string;
  title: string;
  severity: string;
  category: string;
  description: string;
  references: string[];
}

interface AuditRuleRowProps {
  rule: AuditRuleData;
  isLast: boolean;
}

export function AuditRuleRow({ rule, isLast }: AuditRuleRowProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={cn(!isLast && 'border-b border-border-subtle', expanded && 'bg-surface-subtle')}
      data-testid="audit-rule-row"
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="grid w-full items-center gap-3 px-3.5 py-2.5 text-left transition-colors hover:bg-surface-hover"
        style={{
          gridTemplateColumns: '20px 90px minmax(0, 1.6fr) minmax(0, 90px) minmax(0, 130px) 80px',
        }}
      >
        {expanded ? (
          <ChevronDown size={12} className="text-fg-tertiary" aria-hidden />
        ) : (
          <ChevronRight size={12} className="text-fg-tertiary" aria-hidden />
        )}
        <SeverityBadge level={severityFromString(rule.severity)} />
        <div className="min-w-0">
          <div className="truncate text-13 font-medium">{rule.title}</div>
          <div className="mono mt-0.5 text-11 text-fg-tertiary">{rule.id}</div>
        </div>
        <span
          className="mono inline-flex w-fit rounded-r-sm bg-surface-subtle px-1.5 py-0.5 text-fg-secondary"
          style={{ fontSize: 11 }}
        >
          {rule.category}
        </span>
        <span className="text-12 text-fg-tertiary">enabled (read-only)</span>
        <span className="mono text-fg-quaternary" style={{ fontSize: 10 }} title="Edit lands in V2">
          —
        </span>
      </button>
      {expanded && (
        <div className="border-t border-border-subtle px-3.5 py-3 text-13 leading-[1.55]">
          <p className="mb-3 max-w-[820px]">{rule.description}</p>
          {rule.references.length > 0 && (
            <ul className="flex flex-wrap gap-3 text-12">
              {rule.references.map((ref) => (
                <li key={ref}>
                  <a
                    href={ref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-brand hover:underline"
                  >
                    {ref}
                    <ExternalLink size={10} strokeWidth={1.8} aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
