import { describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';
import { makePaginatedFindings } from '@/test-utils/fixtures';

import { FindingsTable } from '../FindingsTable';

describe('FindingsTable', () => {
  it('renders one row per finding', () => {
    const page = makePaginatedFindings();
    const { container } = renderWithProviders(
      <FindingsTable findings={page.items} isDev={false} />,
    );
    const rows = container.querySelectorAll('tbody > tr');
    // Each finding contributes 1 row when collapsed.
    expect(rows.length).toBe(page.items.length);
  });

  it('toggles inline expansion on row click and shows the 5 sections', async () => {
    const user = userEvent.setup();
    const page = makePaginatedFindings();
    const { container, findByText } = renderWithProviders(
      <FindingsTable findings={page.items} isDev={false} />,
    );
    const firstRow = container.querySelector('tbody > tr') as HTMLElement;
    await user.click(firstRow);
    expect(await findByText(/Why this fired/i)).toBeInTheDocument();
    expect(await findByText(/Affected objects/i)).toBeInTheDocument();
    expect(await findByText(/Evidence/i)).toBeInTheDocument();
    expect(await findByText(/Remediation/i)).toBeInTheDocument();
    expect(await findByText(/References/i)).toBeInTheDocument();
  });

  it('shows empty state when no findings provided', () => {
    const { getByText } = renderWithProviders(<FindingsTable findings={[]} isDev={false} />);
    expect(getByText(/No findings above the current filter/i)).toBeInTheDocument();
  });
});
