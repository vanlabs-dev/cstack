'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { Button } from '@/components/ui/Button';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export function Pagination({ total, limit, offset, hasMore }: PaginationProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const setOffset = (next: number): void => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 0) params.delete('offset');
    else params.set('offset', String(next));
    router.push(`${pathname}?${params.toString()}` as never);
  };

  const page = Math.floor(offset / Math.max(limit, 1)) + 1;
  const lastPage = Math.max(1, Math.ceil(total / Math.max(limit, 1)));

  return (
    <div className="mt-3 flex items-center justify-between text-12 text-fg-tertiary">
      <span className="mono">
        page {page} of {lastPage} · {total} total
      </span>
      <div className="flex items-center gap-1.5">
        <Button
          variant="ghost"
          size="sm"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - limit))}
        >
          <ChevronLeft size={12} aria-hidden />
          Previous
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={!hasMore}
          onClick={() => setOffset(offset + limit)}
        >
          Next
          <ChevronRight size={12} aria-hidden />
        </Button>
      </div>
    </div>
  );
}
