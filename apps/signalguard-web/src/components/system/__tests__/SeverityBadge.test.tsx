import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { SeverityBadge, severityFromString } from '../SeverityBadge';

describe('SeverityBadge', () => {
  it.each([
    ['crit', 'sev-crit'],
    ['high', 'sev-high'],
    ['med', 'sev-med'],
    ['low', 'sev-low'],
    ['info', 'sev-info'],
  ] as const)('renders shape class for %s', (level, className) => {
    const { container } = renderWithProviders(<SeverityBadge level={level} />);
    const root = container.querySelector('.sev');
    expect(root).not.toBeNull();
    expect(root?.className).toContain(className);
    expect(container.querySelector('.sev-shape')).not.toBeNull();
  });

  it('uses default labels per level', () => {
    const { getByText } = renderWithProviders(<SeverityBadge level="crit" />);
    expect(getByText('Critical')).toBeInTheDocument();
  });

  it('supports custom label override', () => {
    const { getByText } = renderWithProviders(<SeverityBadge level="high" label="Alert" />);
    expect(getByText('Alert')).toBeInTheDocument();
  });
});

describe('severityFromString', () => {
  it.each([
    ['CRITICAL', 'crit'],
    ['HIGH', 'high'],
    ['MEDIUM', 'med'],
    ['LOW', 'low'],
    ['INFO', 'info'],
    ['unknown', 'info'],
    [null, 'info'],
  ])('maps %s to %s', (input, expected) => {
    expect(severityFromString(input)).toBe(expected);
  });
});
