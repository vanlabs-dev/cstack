import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';
import { tenantA } from '@/test-utils/fixtures';

vi.mock('next-themes', () => {
  const setTheme = vi.fn();
  return {
    useTheme: () => ({ theme: 'light', setTheme }),
    ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    __setTheme: setTheme,
  };
});

import { GeneralForm } from '../GeneralForm';

describe('GeneralForm', () => {
  it('persists default tenant + density to localStorage on save', async () => {
    const user = userEvent.setup();
    window.localStorage.clear();
    const { getByText, getByDisplayValue, container } = renderWithProviders(
      <GeneralForm tenants={[tenantA]} activeTenantId={tenantA.tenant_id} />,
    );
    expect(getByDisplayValue(tenantA.display_name)).toBeInTheDocument();

    const select = container.querySelector('select') as HTMLSelectElement;
    await user.selectOptions(select, tenantA.tenant_id);
    await user.click(getByText('comfortable'));
    await user.click(getByText('Save preferences'));

    expect(window.localStorage.getItem('cstack-default-tenant')).toBe(tenantA.tenant_id);
    expect(window.localStorage.getItem('cstack-density')).toBe('comfortable');
  });
});
