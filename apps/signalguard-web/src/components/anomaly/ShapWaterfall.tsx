'use client';

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, type TooltipProps } from 'recharts';

import type { ShapFeatureContribution } from '@/lib/api/generated/types.gen';

interface ShapWaterfallProps {
  contributions: ShapFeatureContribution[];
  baseScore: number;
  normalisedScore: number;
}

interface RowDatum {
  feature: string;
  value: number;
  shap: number;
  direction: 'pushes_anomalous' | 'pushes_normal';
  raw: ShapFeatureContribution;
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const datum = payload[0]?.payload as RowDatum | undefined;
  if (!datum) return null;
  return (
    <div
      className="rounded-r border border-border bg-surface px-2.5 py-1.5 text-12"
      style={{ boxShadow: 'var(--shadow-pop)' }}
    >
      <div className="mb-0.5 font-medium">{datum.feature}</div>
      <div className="mono text-fg-tertiary">
        value: {datum.value.toFixed(2)} · shap: {datum.shap.toFixed(3)}
      </div>
      <div
        className="mono"
        style={{
          color: datum.direction === 'pushes_anomalous' ? 'var(--color-crit)' : 'var(--color-ok)',
        }}
      >
        {datum.direction.replace('_', ' ')}
      </div>
    </div>
  );
}

export function ShapWaterfall({ contributions, baseScore, normalisedScore }: ShapWaterfallProps) {
  if (contributions.length === 0) {
    return (
      <div className="overflow-hidden rounded-r-md border border-border bg-surface">
        <div className="border-b border-border px-3.5 py-3">
          <div className="text-13 font-semibold">Score contribution</div>
        </div>
        <div className="px-3.5 py-6 text-13 text-fg-tertiary">
          No SHAP attribution captured for this sign-in.
        </div>
      </div>
    );
  }
  const sorted: RowDatum[] = [...contributions]
    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    .map((c) => ({
      feature: c.feature_name,
      value: c.feature_value,
      shap: c.shap_value,
      direction: c.direction,
      raw: c,
    }));
  return (
    <div className="overflow-hidden rounded-r-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
        <div>
          <div className="text-13 font-semibold">Score contribution</div>
          <div className="mt-0.5 text-11 text-fg-tertiary">SHAP values, sorted by magnitude</div>
        </div>
        <span className="num mono text-16 font-semibold">{(normalisedScore * 100).toFixed(0)}</span>
      </div>
      <div className="px-3.5 py-3">
        <div className="space-y-1.5">
          {sorted.map((row) => {
            const sign = row.direction === 'pushes_anomalous' ? '+' : '−';
            const colour =
              row.direction === 'pushes_anomalous' ? 'var(--color-crit)' : 'var(--color-ok)';
            return (
              <div
                key={row.feature}
                className="grid items-center gap-2"
                style={{ gridTemplateColumns: '1fr 60px' }}
              >
                <div>
                  <div className="mb-0.5 text-12">{row.feature}</div>
                  <div className="relative h-1.5 rounded-sm bg-surface-subtle">
                    <div className="absolute left-1/2 top-0 bottom-0 w-px bg-border-strong" />
                    <div
                      className="absolute top-0 bottom-0 rounded-sm"
                      style={{
                        left:
                          row.direction === 'pushes_anomalous'
                            ? '50%'
                            : `${50 - Math.min(Math.abs(row.shap), 0.5) * 100}%`,
                        width: `${Math.min(Math.abs(row.shap), 0.5) * 100}%`,
                        background: colour,
                        opacity: 0.85,
                      }}
                    />
                  </div>
                </div>
                <span className="num mono text-right text-11 font-medium" style={{ color: colour }}>
                  {sign}
                  {Math.abs(row.shap).toFixed(2)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="mt-3 hidden" aria-hidden style={{ height: 0, width: 0 }}>
          <ResponsiveContainer width="100%" height={0}>
            <BarChart data={sorted}>
              <Bar dataKey="shap">
                {sorted.map((d) => (
                  <Cell
                    key={d.feature}
                    fill={
                      d.direction === 'pushes_anomalous' ? 'var(--color-crit)' : 'var(--color-ok)'
                    }
                  />
                ))}
              </Bar>
              <Tooltip content={<CustomTooltip />} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3 text-11 text-fg-tertiary">
          base rate {(baseScore * 100).toFixed(0)} → score {(normalisedScore * 100).toFixed(0)}
        </div>
      </div>
    </div>
  );
}
