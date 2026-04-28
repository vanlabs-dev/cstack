import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { ProtectionBadge } from '../ProtectionBadge';

describe('ProtectionBadge', () => {
  it.each([
    [4, 'MFA + device'],
    [3, 'MFA enforced'],
    [2, 'Device only'],
    [1, 'Report-only'],
    [0, 'Unprotected'],
  ] as const)('renders level %s as %s', (level, label) => {
    const { getByLabelText } = renderWithProviders(<ProtectionBadge level={level} />);
    expect(getByLabelText(label)).toBeInTheDocument();
  });

  it('renders large size with text label', () => {
    const { getByText } = renderWithProviders(<ProtectionBadge level={4} size="lg" />);
    expect(getByText('MFA + device')).toBeInTheDocument();
  });
});
