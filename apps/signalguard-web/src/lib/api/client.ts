/**
 * Hand-written wrapper around the generated @hey-api/client-fetch client.
 *
 * Responsibilities:
 *  - Resolve API base URL from NEXT_PUBLIC_API_BASE_URL.
 *  - Attach X-API-Key on every request using the dev key the user entered.
 *  - Generate a per-request X-Correlation-Id (UUID v4) so the server log
 *    trail can be matched to a UI action.
 *  - Map non-2xx responses to a typed ApiError exposing the RFC-7807 fields.
 *
 * The generated client lives at `lib/api/generated/`; never edit it.
 */

import { createClient, createConfig } from '@hey-api/client-fetch';

import { resolveApiKey } from './auth';

const DEFAULT_BASE_URL = 'http://localhost:8000';

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  correlation_id: string;
  instance?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly type: string;
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string;
  readonly instance?: string | null;

  constructor(problem: ProblemDetail) {
    super(`${problem.title}: ${problem.detail}`);
    this.name = 'ApiError';
    this.status = problem.status;
    this.type = problem.type;
    this.title = problem.title;
    this.detail = problem.detail;
    this.correlationId = problem.correlation_id;
    this.instance = problem.instance;
  }
}

function generateCorrelationId(): string {
  if (
    typeof globalThis.crypto !== 'undefined' &&
    typeof globalThis.crypto.randomUUID === 'function'
  ) {
    return globalThis.crypto.randomUUID();
  }
  return `cs-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

let cachedClient: ReturnType<typeof createClient> | null = null;

function buildClient(): ReturnType<typeof createClient> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;
  const instance = createClient(createConfig({ baseUrl }));

  instance.interceptors.request.use(async (request) => {
    const key = await resolveApiKey();
    if (key) {
      request.headers.set('X-API-Key', key);
    }
    request.headers.set('X-Correlation-Id', generateCorrelationId());
    return request;
  });

  instance.interceptors.response.use(async (response) => {
    if (response.ok) return response;
    const text = await response.clone().text();
    let problem: ProblemDetail;
    try {
      problem = JSON.parse(text) as ProblemDetail;
    } catch {
      problem = {
        type: 'https://signalguard.dev/errors/unknown',
        title: response.statusText || 'Error',
        status: response.status,
        detail: text || `Request failed with status ${response.status}`,
        correlation_id: response.headers.get('X-Correlation-Id') ?? '',
      };
    }
    throw new ApiError(problem);
  });

  return instance;
}

export function apiClient(): ReturnType<typeof createClient> {
  if (cachedClient === null) {
    cachedClient = buildClient();
  }
  return cachedClient;
}

export function resetApiClient(): void {
  cachedClient = null;
}
