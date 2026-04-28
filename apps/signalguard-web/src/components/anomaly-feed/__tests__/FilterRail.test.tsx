import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';

import { FilterRail } from '../FilterRail';

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard/anomalies',
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams('tenant=00000000-aaaa-1111-1111-111111111111'),
}));

describe('FilterRail', () => {
  it('clicking a time range chip pushes a since param', async () => {
    pushMock.mockClear();
    const user = userEvent.setup();
    const { getByText } = renderWithProviders(<FilterRail />);
    await user.click(getByText('24h'));
    expect(pushMock).toHaveBeenCalledTimes(1);
    expect(pushMock.mock.calls[0]?.[0]).toContain('range=24h');
    expect(pushMock.mock.calls[0]?.[0]).toContain('since=');
  });

  it('clicking the All severity chip removes min_score', async () => {
    pushMock.mockClear();
    const user = userEvent.setup();
    const { getByText } = renderWithProviders(<FilterRail />);
    await user.click(getByText('Med+'));
    expect(pushMock.mock.calls[0]?.[0]).toContain('min_score=0.85');
  });

  it('Dismissed and Known-good buttons are disabled placeholders', () => {
    const { getByRole } = renderWithProviders(<FilterRail />);
    expect(getByRole('button', { name: 'Dismissed' })).toBeDisabled();
    expect(getByRole('button', { name: 'Known-good' })).toBeDisabled();
  });
});
