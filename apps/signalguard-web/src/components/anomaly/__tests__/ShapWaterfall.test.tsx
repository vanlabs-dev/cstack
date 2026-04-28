import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';
import { anomalyScores } from '@/test-utils/fixtures';

import { ShapWaterfall } from '../ShapWaterfall';

describe('ShapWaterfall', () => {
  it('renders waterfall when contributions are present', () => {
    const score = anomalyScores[0]!;
    const { getByTestId, getByText } = renderWithProviders(
      <ShapWaterfall
        contributions={score.shap_top_features ?? []}
        baseScore={0.12}
        normalisedScore={score.normalised_score}
      />,
    );
    expect(getByTestId('shap-waterfall')).toBeInTheDocument();
    expect(getByText(/base rate 12 → score/)).toBeInTheDocument();
  });

  it('renders empty-state copy when no contributions are given', () => {
    const { getByText } = renderWithProviders(
      <ShapWaterfall contributions={[]} baseScore={0.12} normalisedScore={0.5} />,
    );
    expect(getByText(/No SHAP attribution captured/)).toBeInTheDocument();
  });
});
