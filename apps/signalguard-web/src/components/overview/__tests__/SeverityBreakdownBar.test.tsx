import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { SeverityBreakdownBar } from '../SeverityBreakdownBar';

describe('SeverityBreakdownBar', () => {
  it('renders all five severity rows with their counts', () => {
    const { getByText, container } = renderWithProviders(
      <SeverityBreakdownBar bySeverity={{ CRITICAL: 4, HIGH: 11, MEDIUM: 8, LOW: 6, INFO: 2 }} />,
    );
    expect(getByText('4')).toBeInTheDocument();
    expect(getByText('11')).toBeInTheDocument();
    expect(getByText('2')).toBeInTheDocument();
    expect(container.querySelectorAll('.sev').length).toBe(5);
  });

  it('handles missing severity buckets', () => {
    const { container } = renderWithProviders(
      <SeverityBreakdownBar bySeverity={{ CRITICAL: 1 }} />,
    );
    expect(container.querySelectorAll('.sev').length).toBe(5);
  });
});
