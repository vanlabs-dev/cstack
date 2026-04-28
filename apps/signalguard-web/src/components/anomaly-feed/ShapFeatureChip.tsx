import type { ShapFeatureContribution } from '@/lib/api/generated/types.gen';

interface ShapFeatureChipProps {
  feature: ShapFeatureContribution;
}

export function ShapFeatureChip({ feature }: ShapFeatureChipProps) {
  const anomalous = feature.direction === 'pushes_anomalous';
  const sign = anomalous ? '+' : '−';
  const colour = anomalous ? 'var(--color-crit)' : 'var(--color-ok)';
  return (
    <span
      className="mono inline-flex items-center gap-1 rounded-r-sm border border-border-subtle bg-surface-subtle px-1.5 py-0.5"
      style={{ fontSize: 11, color: 'var(--color-fg-secondary)' }}
      role="img"
      aria-label={`${feature.feature_name}, ${feature.direction.replace('_', ' ')}`}
    >
      <span style={{ color: colour, fontWeight: 600 }}>{sign}</span>
      {feature.feature_name}
    </span>
  );
}
