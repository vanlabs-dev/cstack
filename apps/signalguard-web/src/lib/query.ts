'use client';

import { QueryClient } from '@tanstack/react-query';

let cached: QueryClient | null = null;

export function getQueryClient(): QueryClient {
  if (cached === null) {
    cached = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          refetchOnWindowFocus: false,
          retry: 1,
        },
      },
    });
  }
  return cached;
}
