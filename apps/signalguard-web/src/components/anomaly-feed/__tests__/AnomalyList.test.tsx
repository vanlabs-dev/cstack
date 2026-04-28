import { describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';
import { anomalyScores, TENANT_A_ID } from '@/test-utils/fixtures';

import { AnomalyList } from '../AnomalyList';

describe('AnomalyList', () => {
  it('renders one row per score', () => {
    const { container } = renderWithProviders(
      <AnomalyList scores={anomalyScores} tenantId={TENANT_A_ID} />,
    );
    expect(container.querySelectorAll('[data-testid="anomaly-row"]').length).toBe(
      anomalyScores.length,
    );
  });

  it('shows bulk actions strip when at least one row is selected', async () => {
    const user = userEvent.setup();
    const { getByLabelText, queryByRole, findByRole } = renderWithProviders(
      <AnomalyList scores={anomalyScores} tenantId={TENANT_A_ID} />,
    );
    expect(queryByRole('region', { name: /Bulk actions/ })).toBeNull();
    const checkbox = getByLabelText(`Select sign-in ${anomalyScores[0]!.signin_id}`);
    await user.click(checkbox);
    expect(await findByRole('region', { name: /Bulk actions/ })).toBeInTheDocument();
  });

  it('renders empty-state copy when zero scores supplied', () => {
    const { getByText } = renderWithProviders(<AnomalyList scores={[]} tenantId={TENANT_A_ID} />);
    expect(getByText(/No anomalies match/)).toBeInTheDocument();
  });
});
