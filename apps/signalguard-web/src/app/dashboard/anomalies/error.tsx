'use client';

import { Button } from '@/components/ui/Button';

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  return (
    <div className="mx-auto mt-12 max-w-[520px] rounded-r-md border border-border bg-surface p-5">
      <p className="eyebrow mb-2">Anomalies request failed</p>
      <h1 className="mb-2 text-16 font-semibold">{error.message}</h1>
      <Button variant="default" onClick={() => reset()}>
        Retry
      </Button>
    </div>
  );
}
