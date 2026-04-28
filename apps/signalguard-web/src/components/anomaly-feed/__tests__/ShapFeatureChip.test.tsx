import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { ShapFeatureChip } from '../ShapFeatureChip';

describe('ShapFeatureChip', () => {
  it('renders a + sign for pushes_anomalous', () => {
    const { getByText, getByLabelText } = renderWithProviders(
      <ShapFeatureChip
        feature={{
          feature_name: 'travel_speed_kmh',
          feature_value: 8000,
          shap_value: -0.4,
          direction: 'pushes_anomalous',
        }}
      />,
    );
    expect(getByText('+')).toBeInTheDocument();
    expect(getByText('travel_speed_kmh')).toBeInTheDocument();
    expect(getByLabelText(/pushes anomalous/)).toBeInTheDocument();
  });

  it('renders a − sign for pushes_normal', () => {
    const { getByText } = renderWithProviders(
      <ShapFeatureChip
        feature={{
          feature_name: 'mfa_satisfied',
          feature_value: 1,
          shap_value: 0.18,
          direction: 'pushes_normal',
        }}
      />,
    );
    expect(getByText('−')).toBeInTheDocument();
  });
});
