/**
 * Unified API key resolver. Server-side reads the cookie via next/headers;
 * client-side reads localStorage. ApiKeyGate writes both, so both paths
 * agree on the same value once the gate has been satisfied.
 */

import { API_KEY_COOKIE, getApiKey as getBrowserApiKey } from "./key-storage";

export async function resolveApiKey(): Promise<string | null> {
  if (typeof window === "undefined") {
    const { cookies } = await import("next/headers");
    const store = await cookies();
    return store.get(API_KEY_COOKIE)?.value ?? null;
  }
  return getBrowserApiKey();
}
