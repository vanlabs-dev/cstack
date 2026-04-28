import { describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '@/test-utils/render';

import { AUDIT_RULES } from '../auditRules';
import { AuditRuleRow } from '../AuditRuleRow';

describe('AuditRuleRow', () => {
  it('renders rule id and severity', () => {
    const rule = AUDIT_RULES[0]!;
    const { getByText } = renderWithProviders(<AuditRuleRow rule={rule} isLast={false} />);
    expect(getByText(rule.id)).toBeInTheDocument();
    expect(getByText(rule.title)).toBeInTheDocument();
  });

  it('expands to show description on click', async () => {
    const user = userEvent.setup();
    const rule = AUDIT_RULES[0]!;
    const { getByRole, findByText } = renderWithProviders(
      <AuditRuleRow rule={rule} isLast={false} />,
    );
    await user.click(getByRole('button'));
    expect(await findByText(rule.description)).toBeInTheDocument();
  });
});
