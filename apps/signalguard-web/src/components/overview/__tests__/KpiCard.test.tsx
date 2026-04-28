import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { KpiCard } from '../KpiCard';

describe('KpiCard', () => {
  it('renders label, value, delta, and sparkline', () => {
    const { getByText, getByTestId } = renderWithProviders(
      <KpiCard label="Critical findings" value={4} delta="+1" trend={[1, 2, 3, 4]} />,
    );
    expect(getByText('Critical findings')).toBeInTheDocument();
    expect(getByText('4')).toBeInTheDocument();
    expect(getByText(/\+1/)).toBeInTheDocument();
    expect(getByTestId('kpi-sparkline')).toBeInTheDocument();
  });

  it('renders footnote in lieu of delta when none given', () => {
    const { getByText, queryByText } = renderWithProviders(
      <KpiCard label="Policies analysed" value={23} footnote="last analysed 2026-04-28" />,
    );
    expect(getByText(/last analysed 2026-04-28/)).toBeInTheDocument();
    expect(queryByText('14d')).toBeNull();
  });

  it('uses crit colour class when deltaTone is bad', () => {
    const { container } = renderWithProviders(
      <KpiCard label="High findings" value={11} delta="+5" deltaTone="bad" />,
    );
    expect(container.innerHTML).toContain('text-crit');
  });
});
