import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { ApiKeyGate } from '../ApiKeyGate';

describe('ApiKeyGate', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.cookie = 'cstack-api-key=; Path=/; Max-Age=0';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the modal when no key is present', () => {
    const { getByText, queryByText } = renderWithProviders(
      <ApiKeyGate>
        <span>app body</span>
      </ApiKeyGate>,
    );
    expect(getByText(/Enter dev API key/)).toBeInTheDocument();
    expect(queryByText('app body')).toBeNull();
  });

  it('renders children when a key is already in localStorage', () => {
    window.localStorage.setItem('cstack-api-key', 'dev-secret');
    const { getByText } = renderWithProviders(
      <ApiKeyGate>
        <span>app body</span>
      </ApiKeyGate>,
    );
    expect(getByText('app body')).toBeInTheDocument();
  });
});
