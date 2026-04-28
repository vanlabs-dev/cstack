import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { Avatar } from '../Avatar';

describe('Avatar', () => {
  it('renders initials from a single-word name', () => {
    const { getByText } = renderWithProviders(<Avatar name="Marcus" />);
    expect(getByText('M')).toBeInTheDocument();
  });

  it('renders two initials from a multi-word name', () => {
    const { getByText } = renderWithProviders(<Avatar name="Helena Roe" />);
    expect(getByText('HR')).toBeInTheDocument();
  });

  it('uses deterministic colour for the same name', () => {
    const { container: a } = renderWithProviders(<Avatar name="Helena Roe" />);
    const { container: b } = renderWithProviders(<Avatar name="Helena Roe" />);
    const aColor = (a.firstChild as HTMLElement).style.background;
    const bColor = (b.firstChild as HTMLElement).style.background;
    expect(aColor).toBe(bColor);
  });
});
