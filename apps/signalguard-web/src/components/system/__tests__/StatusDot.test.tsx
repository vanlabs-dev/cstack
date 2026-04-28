import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { StatusDot } from '../StatusDot';

describe('StatusDot', () => {
  it.each([
    ['ok', 'dot-ok', 'Healthy'],
    ['warn', 'dot-warn', 'Stale'],
    ['err', 'dot-err', 'Failed'],
    ['idle', 'dot-idle', 'Idle'],
  ] as const)('renders %s kind with class %s', (kind, cls, label) => {
    const { container, getByLabelText } = renderWithProviders(<StatusDot kind={kind} />);
    expect(container.querySelector(`.${cls}`)).not.toBeNull();
    expect(getByLabelText(label)).toBeInTheDocument();
  });
});
