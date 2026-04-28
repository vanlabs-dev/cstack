import { describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';
import { coverageMatrix, TENANT_A_ID } from '@/test-utils/fixtures';

import { CoverageHeatmap } from '../CoverageHeatmap';

describe('CoverageHeatmap', () => {
  it('renders 25 grid cells plus the column headers', () => {
    const { container } = renderWithProviders(
      <CoverageHeatmap matrix={coverageMatrix} tenantId={TENANT_A_ID} />,
    );
    const cells = container.querySelectorAll('button[role="gridcell"]');
    expect(cells.length).toBe(25);
  });

  it('opens the side panel when a cell is clicked', async () => {
    const user = userEvent.setup();
    const { container, findByRole } = renderWithProviders(
      <CoverageHeatmap matrix={coverageMatrix} tenantId={TENANT_A_ID} />,
    );
    const cells = container.querySelectorAll('button[role="gridcell"]');
    await user.click(cells[0]!);
    const dialog = await findByRole('dialog');
    expect(dialog).toBeInTheDocument();
  });

  it('closes the side panel via the close button', async () => {
    const user = userEvent.setup();
    const { container, findByRole, queryByRole } = renderWithProviders(
      <CoverageHeatmap matrix={coverageMatrix} tenantId={TENANT_A_ID} />,
    );
    const cells = container.querySelectorAll('button[role="gridcell"]');
    await user.click(cells[0]!);
    const dialog = await findByRole('dialog');
    const close = dialog.querySelector('button[aria-label="Close panel"]') as HTMLButtonElement;
    await user.click(close);
    expect(queryByRole('dialog')).toBeNull();
  });
});
