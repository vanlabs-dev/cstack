/**
 * Helpers to stub the typed call surface in lib/api/calls.ts. Tests that
 * render server components are awkward in vitest; we import the page's
 * client subtree directly with mocked call wrappers.
 */

import { vi } from 'vitest';

export function mockCallsModule(overrides: Record<string, unknown> = {}) {
  vi.mock('@/lib/api/calls', () => ({
    callListTenants: vi.fn(),
    callTenantDetail: vi.fn(),
    callListFindings: vi.fn(),
    callFinding: vi.fn(),
    callFindingsSummary: vi.fn(),
    callListAnomalyScores: vi.fn(),
    callAnomalyFeed: vi.fn(),
    callAnomalyDetail: vi.fn(),
    callCoverageMatrix: vi.fn(),
    callSigninStats: vi.fn(),
    callUserSignins: vi.fn(),
    callRunAudit: vi.fn(),
    callScoreAnomaly: vi.fn(),
    callListModels: vi.fn(),
    callListApiKeys: vi.fn(),
    callCreateApiKey: vi.fn(),
    callDeleteApiKey: vi.fn(),
    ...overrides,
  }));
}
