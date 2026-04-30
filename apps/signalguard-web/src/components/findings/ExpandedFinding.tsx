'use client';

import { Bookmark, Check, ExternalLink } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

import type { Finding } from '@/lib/api/generated/types.gen';

import { CopyButton } from './CopyButton';
import { EvidenceJson } from './EvidenceJson';
import { FindingNarrative } from './FindingNarrative';

interface ExpandedFindingProps {
  finding: Finding;
  isDev: boolean;
}

function splitRemediation(text: string): string[] {
  if (!text) return [];
  const parts = text.split(/(?:\r?\n){2,}/).filter(Boolean);
  if (parts.length > 1) return parts;
  return text
    .split(/(?<=[.!?])\s+(?=[A-Z])/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function entraPortalUrl(finding: Finding): string {
  const policyObj = finding.affected_objects?.find((o) => o.type === 'policy');
  if (policyObj && policyObj.id) {
    return `https://entra.microsoft.com/#view/Microsoft_AAD_ConditionalAccess/PolicyBlade/policyId/${encodeURIComponent(policyObj.id)}`;
  }
  return 'https://entra.microsoft.com/';
}

export function ExpandedFinding({ finding, isDev }: ExpandedFindingProps) {
  const evidence = (finding.evidence ?? {}) as Record<string, unknown>;
  const summary = finding.summary ?? '';
  const remediationSteps = splitRemediation(finding.remediation_hint ?? '');
  const references = finding.references ?? [];
  return (
    <div className="bg-surface-subtle px-5 py-4">
      <Section eyebrow="Why this fired">
        {summary ? (
          <p className="text-13 leading-[1.55] text-fg">{summary}</p>
        ) : (
          <p className="text-13 italic text-fg-tertiary">(rule-supplied summary unavailable)</p>
        )}
      </Section>

      <Section eyebrow="Narrative">
        <FindingNarrative tenantId={finding.tenant_id} findingId={finding.id} isDev={isDev} />
      </Section>

      <Section eyebrow="Affected objects">
        {finding.affected_objects && finding.affected_objects.length > 0 ? (
          <ul className="space-y-1.5">
            {finding.affected_objects.map((obj) => (
              <li key={`${obj.type}-${obj.id}`} className="flex items-center gap-2 text-13">
                <span className="rounded-r-sm bg-surface px-1.5 py-0.5 text-11 font-medium uppercase text-fg-secondary">
                  {obj.type}
                </span>
                <span className="text-fg">{obj.display_name}</span>
                <span className="mono text-11 text-fg-tertiary">{obj.id}</span>
                <CopyButton text={obj.id} label="Copy id" />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-13 text-fg-tertiary">No affected objects recorded.</p>
        )}
      </Section>

      <Section eyebrow="Evidence">
        <EvidenceJson evidence={evidence} />
      </Section>

      <Section eyebrow="Remediation">
        {remediationSteps.length > 0 ? (
          <ol className="space-y-1.5">
            {remediationSteps.map((step, i) => (
              <li
                key={i}
                className="grid gap-2.5 text-13 leading-[1.5]"
                style={{ gridTemplateColumns: '20px 1fr' }}
              >
                <span className="mono text-fg-quaternary">{i + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-13 text-fg-tertiary">No remediation hint recorded.</p>
        )}
      </Section>

      <Section eyebrow="References" lastSection>
        {references.length > 0 ? (
          <ul className="flex flex-wrap gap-3 text-12">
            {references.map((ref) => (
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
        ) : (
          <p className="text-13 text-fg-tertiary">No external references.</p>
        )}
      </Section>

      <div className="flex flex-wrap items-center gap-1.5 pt-3">
        <Button
          variant="ghost"
          size="default"
          aria-label="Snooze finding"
          title="Snooze flow lands in Sprint 5b"
        >
          <Bookmark size={12} aria-hidden />
          Snooze
        </Button>
        <Button
          variant="ghost"
          size="default"
          aria-label="Mark resolved"
          title="Mutation flow lands in Sprint 5b"
        >
          <Check size={12} aria-hidden />
          Mark resolved
        </Button>
        <CopyButton
          text={JSON.stringify(finding, null, 2)}
          label="Copy as JSON"
          className="h-7 px-2.5"
        />
        <a
          href={entraPortalUrl(finding)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-7 items-center gap-1.5 rounded-r border border-border bg-surface px-2.5 text-13 font-medium text-fg transition-colors hover:bg-surface-hover hover:border-border-strong"
        >
          <ExternalLink size={12} strokeWidth={1.6} aria-hidden />
          Open in Entra portal
        </a>
      </div>
    </div>
  );
}

interface SectionProps {
  eyebrow: string;
  children: React.ReactNode;
  lastSection?: boolean;
}

function Section({ eyebrow, children, lastSection = false }: SectionProps) {
  return (
    <section className={cn('py-3', !lastSection && 'border-b border-border-subtle')}>
      <p className="eyebrow mb-2">{eyebrow}</p>
      {children}
    </section>
  );
}
