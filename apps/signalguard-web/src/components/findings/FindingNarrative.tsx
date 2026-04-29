'use client';

import { formatDistanceToNow } from 'date-fns';
import { RefreshCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { useNarrativeQuery, useRegenerateNarrative } from '@/components/findings/hooks';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

interface FindingNarrativeProps {
  tenantId: string;
  findingId: string;
  isDev: boolean;
}

const SECTION_HEADINGS = ['Why this fired', 'What it means', 'Remediation', 'Caveats'] as const;

type SectionMap = Record<(typeof SECTION_HEADINGS)[number], string>;

function splitMarkdownSections(markdown: string): SectionMap {
  // Split on `## ` headings; first chunk is preamble (always empty for our prompt).
  const parts = markdown.split(/^## /m).slice(1);
  const out = {} as SectionMap;
  for (const part of parts) {
    const newlineIdx = part.indexOf('\n');
    if (newlineIdx === -1) continue;
    const heading = part.slice(0, newlineIdx).trim();
    const body = part.slice(newlineIdx + 1).trim();
    if (SECTION_HEADINGS.includes(heading as (typeof SECTION_HEADINGS)[number])) {
      out[heading as (typeof SECTION_HEADINGS)[number]] = body;
    }
  }
  return out;
}

export function FindingNarrative({ tenantId, findingId, isDev }: FindingNarrativeProps) {
  const query = useNarrativeQuery(tenantId, findingId);
  const regenerate = useRegenerateNarrative(tenantId, findingId);

  if (query.isLoading) {
    return <NarrativeSkeleton />;
  }
  if (query.isError) {
    return (
      <NarrativeError
        message={(query.error as Error)?.message ?? 'failed to load narrative'}
        onRetry={() => regenerate.mutate({ prompt_version: 'v1' })}
        retrying={regenerate.isPending}
        canRegenerate={isDev}
      />
    );
  }
  if (!query.data) return null;

  const sections = splitMarkdownSections(query.data.markdown);
  const generatedRel = formatDistanceToNow(new Date(query.data.generated_at), {
    addSuffix: true,
  });

  return (
    <div className="space-y-3">
      {SECTION_HEADINGS.slice(1).map((heading) => {
        const body = sections[heading];
        if (!body) return null;
        return (
          <section key={heading}>
            <p className="eyebrow mb-1.5">{heading}</p>
            <NarrativeBody markdown={body} />
          </section>
        );
      })}
      <div className="flex items-center justify-between pt-1 text-11 text-fg-tertiary">
        <span className="mono">
          narrative · {query.data.provider}/{query.data.model} · {generatedRel}
          {query.data.cached ? ' · cached' : ''}
        </span>
        {isDev ? (
          <Button
            variant="ghost"
            size="default"
            disabled={regenerate.isPending}
            onClick={() => {
              if (
                window.confirm(
                  'Regenerate narrative? This calls the LLM provider and costs real money.',
                )
              ) {
                regenerate.mutate({ prompt_version: 'v1' });
              }
            }}
            aria-label="Regenerate narrative"
          >
            <RefreshCcw size={11} strokeWidth={1.7} aria-hidden />
            {regenerate.isPending ? 'Regenerating' : 'Regenerate'}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function NarrativeBody({ markdown }: { markdown: string }) {
  return (
    <div className={cn('text-13 leading-[1.55] text-fg', 'narrative-md')}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        // Disallow raw HTML to defend against narrative content trying to inject markup.
        skipHtml
        components={{
          ol: ({ children, ...props }) => (
            <ol className="ml-4 list-decimal space-y-1" {...props}>
              {children}
            </ol>
          ),
          ul: ({ children, ...props }) => (
            <ul className="ml-4 list-disc space-y-1" {...props}>
              {children}
            </ul>
          ),
          code: ({ children, ...props }) => (
            <code
              className="rounded-r-sm bg-surface-subtle px-1 py-0.5 mono text-12 text-fg"
              {...props}
            >
              {children}
            </code>
          ),
          a: ({ children, ...props }) => (
            <a className="text-brand hover:underline" {...props}>
              {children}
            </a>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

function NarrativeSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading narrative">
      {[60, 80, 70, 50].map((width, i) => (
        <div key={i} className="space-y-1.5">
          <div className="h-2.5 w-20 animate-pulse rounded-r-sm bg-surface-subtle" />
          <div
            className="h-3 animate-pulse rounded-r-sm bg-surface-subtle"
            style={{ width: `${width}%` }}
          />
        </div>
      ))}
    </div>
  );
}

interface NarrativeErrorProps {
  message: string;
  onRetry: () => void;
  retrying: boolean;
  canRegenerate: boolean;
}

function NarrativeError({ message, onRetry, retrying, canRegenerate }: NarrativeErrorProps) {
  return (
    <div className="rounded-r-sm border border-border-subtle bg-surface-subtle px-3 py-2 text-12 text-fg-tertiary">
      <p className="mb-1.5">narrative unavailable: {message}</p>
      {canRegenerate ? (
        <Button variant="ghost" size="default" onClick={onRetry} disabled={retrying}>
          <RefreshCcw size={11} strokeWidth={1.7} aria-hidden />
          {retrying ? 'Retrying' : 'Retry'}
        </Button>
      ) : null}
    </div>
  );
}
