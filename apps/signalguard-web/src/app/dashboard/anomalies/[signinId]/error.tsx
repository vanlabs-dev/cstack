'use client';

import { Button } from '@/components/ui/Button';

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  return (
    <div className="mx-auto mt-12 max-w-[520px] rounded-r-md border border-border bg-surface p-5">
      <p className="eyebrow mb-2">Anomaly detail failed</p>
      <h1 className="mb-2 text-16 font-semibold">{error.message}</h1>
      <p className="mb-3 text-13 text-fg-secondary">
        The sign-in might not yet have a score. Run{' '}
        <code className="mono text-fg">cstack anomaly score --tenant &lt;id&gt;</code> and try
        again.
      </p>
      <Button variant="default" onClick={() => reset()}>
        Retry
      </Button>
    </div>
  );
}
