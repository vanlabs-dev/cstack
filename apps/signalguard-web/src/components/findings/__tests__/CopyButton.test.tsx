import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent } from '@testing-library/react';

import { renderWithProviders } from '@/test-utils/render';

import { CopyButton } from '../CopyButton';

describe('CopyButton', () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, 'clipboard', {
      configurable: true,
      writable: true,
      value: { writeText },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls navigator.clipboard.writeText with the supplied text', async () => {
    const { getByRole } = renderWithProviders(<CopyButton text="hello world" />);
    fireEvent.click(getByRole('button'));
    // Wait one microtask so the awaited writeText resolves.
    await Promise.resolve();
    expect(writeText).toHaveBeenCalledWith('hello world');
  });
});
