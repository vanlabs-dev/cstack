import { Shield } from 'lucide-react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { TopBar } from '../TopBar';

describe('TopBar', () => {
  it('renders crumbs in order', () => {
    const { getByText } = renderWithProviders(
      <TopBar
        crumbs={[
          { label: 'SignalGuard', pill: true, pillIcon: Shield },
          { label: 'tenant-a' },
          { label: 'Findings' },
        ]}
      />,
    );
    expect(getByText('SignalGuard')).toBeInTheDocument();
    expect(getByText('tenant-a')).toBeInTheDocument();
    expect(getByText('Findings')).toBeInTheDocument();
  });

  it('renders actions when provided', () => {
    const { getByText } = renderWithProviders(
      <TopBar crumbs={[{ label: 'Home' }]} actions={<button>Sync</button>} />,
    );
    expect(getByText('Sync')).toBeInTheDocument();
  });
});
