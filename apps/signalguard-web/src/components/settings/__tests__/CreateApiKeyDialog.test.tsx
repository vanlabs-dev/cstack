import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';

vi.mock('@/lib/api/calls', () => ({
  callCreateApiKey: vi.fn(async () => ({
    key: 'plaintext-secret-xyz',
    key_label: 'dashboard',
    created_at: '2026-04-28T00:00:00Z',
  })),
}));

import { callCreateApiKey } from '@/lib/api/calls';
import { CreateApiKeyDialog } from '../CreateApiKeyDialog';

describe('CreateApiKeyDialog', () => {
  it('shows the plaintext key once after submit and only once', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onCreated = vi.fn();
    const { getByLabelText, getByRole, findByDisplayValue } = renderWithProviders(
      <CreateApiKeyDialog
        tenantId="00000000-aaaa-1111-1111-111111111111"
        open
        onClose={onClose}
        onCreated={onCreated}
      />,
    );
    const input = getByLabelText(/Label/);
    await user.clear(input);
    await user.type(input, 'dashboard');
    await user.click(getByRole('button', { name: /Create key/ }));
    expect(callCreateApiKey).toHaveBeenCalledWith('00000000-aaaa-1111-1111-111111111111', {
      label: 'dashboard',
    });
    expect(await findByDisplayValue('plaintext-secret-xyz')).toBeInTheDocument();
    expect(onCreated).toHaveBeenCalledTimes(1);
  });
});
