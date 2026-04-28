'use client';

import { Button } from '@/components/ui/Button';

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  return (
    <div className="rounded-r-md border border-border bg-surface p-5">
      <p className="eyebrow mb-2">Settings request failed</p>
      <h2 className="mb-2 text-16 font-semibold">{error.message}</h2>
      <Button variant="default" onClick={() => reset()}>
        Retry
      </Button>
    </div>
  );
}
