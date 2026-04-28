'use client';

import { Check, Copy } from 'lucide-react';
import { useState } from 'react';

import { cn } from '@/lib/cn';

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

export function CopyButton({ text, label = 'Copy', className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const onClick = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // clipboard not granted; ignore silently per design's understated tone
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={copied ? 'Copied' : label}
      className={cn(
        'inline-flex h-6 items-center gap-1 rounded-r-sm border border-border bg-surface px-1.5 text-12 text-fg-tertiary transition-colors hover:bg-surface-hover hover:text-fg',
        className,
      )}
    >
      {copied ? <Check size={11} aria-hidden /> : <Copy size={11} aria-hidden />}
      {copied ? 'Copied' : label}
    </button>
  );
}
