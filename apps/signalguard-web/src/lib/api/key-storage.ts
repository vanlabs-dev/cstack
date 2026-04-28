/**
 * Dev API key persistence on the browser.
 *
 * The plan: store the key in localStorage so the gate UI can read and write
 * it, AND mirror it as a cookie so server components can authenticate
 * against the API on the same key. The cookie is httpOnly=false on purpose;
 * this is dev-only auth, not a production credential store.
 */

const STORAGE_KEY = 'cstack-api-key';
const COOKIE_NAME = 'cstack-api-key';
const COOKIE_MAX_AGE_S = 60 * 60 * 24 * 365;

const isBrowser = (): boolean => typeof window !== 'undefined';

export function getApiKey(): string | null {
  if (!isBrowser()) return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setApiKey(value: string): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // localStorage disabled (private mode); cookie alone keeps SSR working.
  }
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(value)}; Path=/; Max-Age=${COOKIE_MAX_AGE_S}; SameSite=Lax`;
}

export function clearApiKey(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore; cookie clear below handles SSR-side state.
  }
  document.cookie = `${COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export const API_KEY_COOKIE = COOKIE_NAME;
