import { describe, expect, it } from 'vitest';

import { AUDIT_RULES } from '../auditRules';

describe('AUDIT_RULES catalogue', () => {
  it('contains all 15 registered rules', () => {
    expect(AUDIT_RULES).toHaveLength(15);
  });

  it('each rule has a unique id', () => {
    const ids = new Set(AUDIT_RULES.map((r) => r.id));
    expect(ids.size).toBe(AUDIT_RULES.length);
  });

  it('every rule has a severity in the canonical set', () => {
    const allowed = new Set(['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
    for (const r of AUDIT_RULES) {
      expect(allowed.has(r.severity)).toBe(true);
    }
  });
});
