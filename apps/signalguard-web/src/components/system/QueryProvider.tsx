'use client';

import { QueryClientProvider } from '@tanstack/react-query';

import { getQueryClient } from '@/lib/query';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const client = getQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
