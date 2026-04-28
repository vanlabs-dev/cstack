import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';

import { FilterChipStrip } from '../FilterChipStrip';

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard/findings',
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams('tenant=00000000-aaaa-1111-1111-111111111111'),
}));

describe('FilterChipStrip', () => {
  it('clicking a severity chip pushes a new URL with min_severity set', async () => {
    pushMock.mockClear();
    const user = userEvent.setup();
    const { getByText } = renderWithProviders(<FilterChipStrip />);
    await user.click(getByText('≥ high'));
    expect(pushMock).toHaveBeenCalledTimes(1);
    expect(pushMock.mock.calls[0]?.[0]).toContain('min_severity=HIGH');
  });

  it('clicking a category chip appends the category param', async () => {
    pushMock.mockClear();
    const user = userEvent.setup();
    const { getByText } = renderWithProviders(<FilterChipStrip />);
    await user.click(getByText('rule'));
    expect(pushMock.mock.calls[0]?.[0]).toContain('category=rule');
  });
});
