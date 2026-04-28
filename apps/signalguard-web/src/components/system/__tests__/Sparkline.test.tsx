import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { KpiSparkline, Sparkline } from '../Sparkline';

describe('Sparkline (svg)', () => {
  it('renders an svg with the right number of polyline points', () => {
    const { container } = renderWithProviders(<Sparkline data={[1, 2, 3, 4, 5]} />);
    const polylines = container.querySelectorAll('polyline');
    expect(polylines.length).toBe(2);
    const points = polylines[1]!.getAttribute('points')!.split(' ');
    expect(points).toHaveLength(5);
  });

  it('renders an empty svg when given fewer than two points', () => {
    const { container } = renderWithProviders(<Sparkline data={[42]} />);
    expect(container.querySelector('svg')).not.toBeNull();
    expect(container.querySelectorAll('polyline').length).toBe(0);
  });
});

describe('KpiSparkline (recharts)', () => {
  it('renders with the test id used by KpiCard', () => {
    const { getByTestId } = renderWithProviders(<KpiSparkline data={[1, 2, 3, 4]} />);
    expect(getByTestId('kpi-sparkline')).toBeInTheDocument();
  });
});
