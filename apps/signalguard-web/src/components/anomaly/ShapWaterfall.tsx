'use client';

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
  XAxis,
  YAxis,
} from 'recharts';

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
  shap_value: number;
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
      // Horizontal bars: anomalous → right (positive), normal → left (negative).
      shap_value:
        c.direction === 'pushes_anomalous' ? Math.abs(c.shap_value) : -Math.abs(c.shap_value),
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
      <div className="px-3.5 py-3" data-testid="shap-waterfall">
        <ResponsiveContainer width="100%" height={Math.max(220, sorted.length * 28)}>
          <BarChart
            data={sorted}
            layout="vertical"
            margin={{ top: 4, right: 56, bottom: 4, left: 12 }}
          >
            <XAxis type="number" hide domain={['dataMin', 'dataMax']} />
            <YAxis
              type="category"
              dataKey="feature"
              tick={{
                fill: 'var(--color-fg-secondary)',
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
              }}
              tickLine={false}
              axisLine={false}
              width={170}
            />
            <Tooltip cursor={{ fill: 'var(--color-surface-hover)' }} content={<CustomTooltip />} />
            <Bar dataKey="shap_value" barSize={14} radius={[2, 2, 2, 2]}>
              {sorted.map((d) => (
                <Cell
                  key={d.feature}
                  fill={
                    d.direction === 'pushes_anomalous' ? 'var(--color-crit)' : 'var(--color-ok)'
                  }
                  fillOpacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-2 text-11 text-fg-tertiary">
          base rate {(baseScore * 100).toFixed(0)} → score {(normalisedScore * 100).toFixed(0)}
        </div>
      </div>
    </div>
  );
}
