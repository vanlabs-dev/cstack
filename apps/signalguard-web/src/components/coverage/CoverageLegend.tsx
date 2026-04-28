import { COVERAGE_LEVEL_INFO } from './ProtectionBadge';

import type { ProtectionLevel } from '@/lib/api/generated/types.gen';

const ORDER: ProtectionLevel[] = [4, 3, 2, 1, 0];

export function CoverageLegend() {
  return (
    <div
      className="flex flex-wrap items-center gap-3 border-t border-border-subtle px-4 py-3"
      role="list"
      aria-label="Coverage levels legend"
    >
      {ORDER.map((level) => {
        const info = COVERAGE_LEVEL_INFO[level];
        return (
          <span
            key={level}
            className="inline-flex items-center gap-1.5 text-fg-secondary"
            style={{ fontSize: 11.5 }}
            role="listitem"
          >
            <span
              className="grid place-items-center rounded-r-sm"
              style={{
                width: 14,
                height: 14,
                background: info.bg,
                color: info.fg,
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                fontWeight: 700,
              }}
              aria-hidden
            >
              {info.icon}
            </span>
            {info.label}
          </span>
        );
      })}
    </div>
  );
}
