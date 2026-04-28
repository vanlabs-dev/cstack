import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard/settings/audit-rules',
  useSearchParams: () => new URLSearchParams('tenant=00000000-aaaa-1111-1111-111111111111'),
}));

import { SettingsTabs } from '../SettingsTabs';

describe('SettingsTabs', () => {
  it('marks the active tab via aria-current', () => {
    const { getByText } = renderWithProviders(<SettingsTabs />);
    const active = getByText('Audit rules').closest('a');
    expect(active?.getAttribute('aria-current')).toBe('page');
  });

  it('shows V2 markers on placeholder tabs', () => {
    const { getAllByText } = renderWithProviders(<SettingsTabs />);
    expect(getAllByText('V2').length).toBeGreaterThanOrEqual(3);
  });
});
