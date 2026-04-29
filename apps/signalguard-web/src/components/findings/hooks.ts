'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { callFindingNarrative, callRegenerateFindingNarrative } from '@/lib/api/calls';

import type { NarrativeResponse, RegenerateRequest } from '@/lib/api/generated/types.gen';

export function narrativeQueryKey(tenantId: string, findingId: string) {
  return ['narrative', tenantId, findingId] as const;
}

export function useNarrativeQuery(tenantId: string, findingId: string) {
  return useQuery<NarrativeResponse>({
    queryKey: narrativeQueryKey(tenantId, findingId),
    queryFn: ({ signal }) => callFindingNarrative(tenantId, findingId, { signal }),
    // Narratives are cached server-side, so a 60-minute client stale time is
    // safe and saves chatter on the findings page. Retry policy inherits from
    // the query client defaults so tests can disable it deterministically.
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

export function useRegenerateNarrative(tenantId: string, findingId: string) {
  const queryClient = useQueryClient();
  return useMutation<NarrativeResponse, Error, RegenerateRequest>({
    mutationFn: (body) => callRegenerateFindingNarrative(tenantId, findingId, body),
    onSuccess: (data) => {
      queryClient.setQueryData(narrativeQueryKey(tenantId, findingId), data);
    },
  });
}
