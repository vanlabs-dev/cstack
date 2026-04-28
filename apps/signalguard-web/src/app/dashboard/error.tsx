'use client';

import { useEffect } from 'react';

import { Button } from '@/components/ui/Button';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

interface ApiErrorShape {
  status?: number;
  title?: string;
  detail?: string;
  correlationId?: string;
}

function asApiError(err: Error & ApiErrorShape): ApiErrorShape | null {
  if (err.name === 'ApiError') return err;
  return null;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error('dashboard error', error);
  }, [error]);

  const apiErr = asApiError(error as Error & ApiErrorShape);

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-6">
      <div className="w-full max-w-[520px] rounded-r-md border border-border bg-surface p-5">
        <p className="eyebrow mb-2">{apiErr ? 'API request failed' : 'Render failed'}</p>
        <h1 className="mb-2 text-16 font-semibold">{apiErr?.title ?? 'Something went wrong'}</h1>
        <p className="mb-3 text-13 text-fg-secondary">
          {apiErr?.detail ?? error.message ?? 'Unknown error'}
        </p>
        {apiErr?.correlationId && (
          <p
            className="mono mb-3 rounded-r border border-border-subtle bg-surface-inset px-2 py-1.5 text-12 text-fg-tertiary"
            aria-label="Correlation id for support"
          >
            correlation_id: {apiErr.correlationId}
          </p>
        )}
        <div className="flex gap-2">
          <Button variant="default" onClick={() => reset()}>
            Retry
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              window.location.href = '/dashboard';
            }}
          >
            Back to home
          </Button>
        </div>
      </div>
    </div>
  );
}
