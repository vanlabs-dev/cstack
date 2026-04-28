import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { Eyebrow } from '../Eyebrow';

describe('Eyebrow', () => {
  it('applies the eyebrow utility class', () => {
    const { getByText } = renderWithProviders(<Eyebrow>Workspace</Eyebrow>);
    const node = getByText('Workspace');
    expect(node.className).toContain('eyebrow');
  });
});
