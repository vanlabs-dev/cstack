import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test-utils/render';

import { FindingNarrative } from '../FindingNarrative';

vi.mock('@/lib/api/calls', () => ({
  callFindingNarrative: vi.fn(),
  callRegenerateFindingNarrative: vi.fn(),
}));

import { callFindingNarrative, callRegenerateFindingNarrative } from '@/lib/api/calls';

const NARRATIVE_FIXTURE = {
  markdown: [
    '## Why this fired',
    'A finding fired because evidence shows missing CA policy.',
    '',
    '## What it means',
    'Without this protection, attackers can land valid credentials.',
    '',
    '## Remediation',
    '1. Step one.',
    '2. Step two.',
    '',
    '## Caveats',
    'Service accounts may need exclusions.',
  ].join('\n'),
  model: 'claude-opus-4-7',
  provider: 'anthropic',
  generated_at: '2026-04-29T09:00:00Z',
  cached: false,
  input_tokens: 100,
  output_tokens: 200,
};

beforeEach(() => {
  vi.mocked(callFindingNarrative).mockReset();
  vi.mocked(callRegenerateFindingNarrative).mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('FindingNarrative', () => {
  it('renders the narrative content when the query succeeds', async () => {
    vi.mocked(callFindingNarrative).mockResolvedValue(NARRATIVE_FIXTURE);
    const { findByText } = renderWithProviders(
      <FindingNarrative tenantId="t-1" findingId="f-1" isDev={false} />,
    );
    expect(await findByText(/What it means/i)).toBeInTheDocument();
    expect(await findByText(/Without this protection/i)).toBeInTheDocument();
  });

  it('shows the regenerate button only when caller is dev', async () => {
    vi.mocked(callFindingNarrative).mockResolvedValue(NARRATIVE_FIXTURE);
    const { findByText, queryByLabelText } = renderWithProviders(
      <FindingNarrative tenantId="t-1" findingId="f-1" isDev={false} />,
    );
    await findByText(/What it means/i);
    expect(queryByLabelText('Regenerate narrative')).toBeNull();
  });

  it('shows the regenerate button when isDev is true', async () => {
    vi.mocked(callFindingNarrative).mockResolvedValue(NARRATIVE_FIXTURE);
    const { findByLabelText } = renderWithProviders(
      <FindingNarrative tenantId="t-1" findingId="f-1" isDev={true} />,
    );
    expect(await findByLabelText('Regenerate narrative')).toBeInTheDocument();
  });

  it('renders an error panel when the narrative fetch fails', async () => {
    vi.mocked(callFindingNarrative).mockRejectedValue(new Error('boom'));
    const { findByText } = renderWithProviders(
      <FindingNarrative tenantId="t-1" findingId="f-1" isDev={true} />,
    );
    expect(await findByText(/narrative unavailable/i)).toBeInTheDocument();
  });
});
