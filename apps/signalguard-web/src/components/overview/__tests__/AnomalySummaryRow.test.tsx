import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';
import { anomalyScores, TENANT_A_ID } from '@/test-utils/fixtures';

import { AnomalySummaryRow } from '../AnomalySummaryRow';

describe('AnomalySummaryRow', () => {
  it('renders user, score, and link to drill-down', () => {
    const score = anomalyScores[0]!;
    const { getByText, container } = renderWithProviders(
      <AnomalySummaryRow score={score} tenantId={TENANT_A_ID} isLast={false} />,
    );
    expect(getByText(score.user_id)).toBeInTheDocument();
    const score100 = Math.round(score.normalised_score * 100);
    expect(getByText(String(score100))).toBeInTheDocument();
    const anchor = container.querySelector('a');
    expect(anchor?.getAttribute('href')).toContain(`/dashboard/anomalies/${score.signin_id}`);
  });
});
