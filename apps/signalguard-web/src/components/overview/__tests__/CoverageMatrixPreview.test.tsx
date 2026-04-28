import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';
import { coverageMatrix, TENANT_A_ID } from '@/test-utils/fixtures';

import { CoverageMatrixPreview } from '../CoverageMatrixPreview';

describe('CoverageMatrixPreview', () => {
  it('renders 5x5 cells plus header row plus column labels', () => {
    const { container, getByText } = renderWithProviders(
      <CoverageMatrixPreview matrix={coverageMatrix} tenantId={TENANT_A_ID} />,
    );
    const cellLinks = container.querySelectorAll('a[href*="coverage"]');
    // 25 cells + 1 header link = 26
    expect(cellLinks.length).toBe(26);
    expect(getByText(/Coverage/)).toBeInTheDocument();
  });
});
