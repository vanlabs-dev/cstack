import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';
import { anomalyDetail } from '@/test-utils/fixtures';

import { MetadataTable } from '../MetadataTable';

describe('MetadataTable', () => {
  it('renders all six grouped sections', () => {
    const { getByText } = renderWithProviders(<MetadataTable signin={anomalyDetail.signin} />);
    for (const eyebrow of [
      'Identity',
      'Time',
      'Location',
      'Network',
      'Device',
      'Auth',
      'Outcome',
    ]) {
      expect(getByText(eyebrow)).toBeInTheDocument();
    }
  });

  it('shows the userPrincipalName from the signin', () => {
    const { getByText } = renderWithProviders(<MetadataTable signin={anomalyDetail.signin} />);
    expect(getByText(anomalyDetail.signin.userPrincipalName)).toBeInTheDocument();
  });
});
