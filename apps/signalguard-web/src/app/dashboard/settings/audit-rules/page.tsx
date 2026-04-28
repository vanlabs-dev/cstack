import { AUDIT_RULES } from '@/components/settings/auditRules';
import { AuditRuleRow } from '@/components/settings/AuditRuleRow';

export default function AuditRulesPage() {
  return (
    <div>
      <div className="mb-3 rounded-r-md border border-border-subtle bg-surface-subtle px-3 py-2 text-12 text-fg-tertiary">
        Per-rule enable/disable lands in V2 with API support. The list below mirrors the rule
        registry in <code className="mono text-fg">cstack-audit-rules</code>; click a row to read
        its description and references.
      </div>
      <div className="overflow-hidden rounded-r-md border border-border bg-surface">
        <div
          className="grid items-center gap-3 border-b border-border bg-surface px-3.5 py-2 text-fg-tertiary"
          style={{
            gridTemplateColumns: '20px 90px minmax(0, 1.6fr) minmax(0, 90px) minmax(0, 130px) 80px',
            fontSize: 11.5,
            fontWeight: 500,
            letterSpacing: '0.02em',
          }}
        >
          <span />
          <span>Severity</span>
          <span>Title</span>
          <span>Category</span>
          <span>Status</span>
          <span>Edit</span>
        </div>
        {AUDIT_RULES.map((rule, i) => (
          <AuditRuleRow key={rule.id} rule={rule} isLast={i === AUDIT_RULES.length - 1} />
        ))}
      </div>
    </div>
  );
}
