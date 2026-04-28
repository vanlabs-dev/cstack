import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';
import { modelSummary, tenantADetail } from '@/test-utils/fixtures';

import { DataFreshnessPanel } from '../DataFreshnessPanel';

describe('DataFreshnessPanel', () => {
  it('renders tenant id, model descriptor, and last sync', () => {
    const { getByText } = renderWithProviders(
      <DataFreshnessPanel tenant={tenantADetail} models={modelSummary} />,
    );
    expect(getByText(/Last sync/)).toBeInTheDocument();
    expect(getByText(tenantADetail.tenant_id)).toBeInTheDocument();
    expect(getByText(/signalguard-anomaly-pooled/)).toBeInTheDocument();
  });

  it('shows fallback when no champion is registered', () => {
    const { getByText } = renderWithProviders(
      <DataFreshnessPanel tenant={tenantADetail} models={[]} />,
    );
    expect(getByText(/no model registered/)).toBeInTheDocument();
  });
});
