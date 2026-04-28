'use client';

import Link from 'next/link';

import { Avatar } from '@/components/system/Avatar';
import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';

import { CountryFlag } from './CountryFlag';
import { ShapFeatureChip } from './ShapFeatureChip';

import type { AnomalyScore, ShapFeatureContribution } from '@/lib/api/generated/types.gen';

export interface AnomalyRowProps {
  score: AnomalyScore;
  signin?: {
    upn?: string | null;
    country?: string | null;
    city?: string | null;
    device?: string | null;
  };
  tenantId: string;
  selected: boolean;
  onSelectChange: (id: string, value: boolean) => void;
}

function scoreColor(score: number): { fg: string; bg: string } {
  if (score >= 0.95) return { fg: 'var(--color-crit)', bg: 'var(--color-crit-bg)' };
  if (score >= 0.85) return { fg: 'var(--color-high)', bg: 'var(--color-high-bg)' };
  if (score >= 0.7) return { fg: 'var(--color-med)', bg: 'var(--color-med-bg)' };
  return { fg: 'var(--color-low)', bg: 'var(--color-low-bg)' };
}

function topThree(features: ShapFeatureContribution[]): ShapFeatureContribution[] {
  return [...features].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value)).slice(0, 3);
}

export function AnomalyRow({ score, signin, tenantId, selected, onSelectChange }: AnomalyRowProps) {
  const colour = scoreColor(score.normalised_score);
  const features = topThree(score.shap_top_features ?? []);
  const country = signin?.country ?? null;
  const upn = signin?.upn ?? score.user_id;
  const city = signin?.city ?? null;
  const device = signin?.device ?? null;
  const href = `/dashboard/anomalies/${encodeURIComponent(score.signin_id)}?tenant=${tenantId}`;
  const isAnomalous = score.is_anomaly;

  return (
    <div
      className={cn(
        'grid items-center gap-2.5 border-b border-border-subtle px-3.5 py-2.5 transition-colors hover:bg-surface-hover last:border-b-0',
        selected && 'bg-surface-subtle',
      )}
      style={{
        gridTemplateColumns:
          '32px minmax(0, 1.4fr) 90px minmax(0, 1.1fr) minmax(0, 1fr) minmax(0, 1.6fr) 64px',
      }}
      data-testid="anomaly-row"
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={(event) => onSelectChange(score.signin_id, event.target.checked)}
        aria-label={`Select sign-in ${score.signin_id}`}
        className="h-3.5 w-3.5 cursor-pointer accent-brand"
      />
      <Link href={href as never} className="flex min-w-0 items-center gap-2.5">
        <Avatar name={score.user_id} size={26} />
        <div className="min-w-0">
          <div className="truncate text-13 font-medium">{score.user_id}</div>
          <div className="mono truncate text-fg-quaternary" style={{ fontSize: 10.5 }}>
            {upn}
          </div>
        </div>
      </Link>
      <Link href={href as never} className="mono" style={{ fontSize: 11.5 }}>
        <div className="text-fg">{formatRelativeTime(score.scored_at)}</div>
        <div className="text-fg-quaternary" style={{ fontSize: 10.5 }}>
          {new Date(score.scored_at).toISOString().slice(11, 19)}
        </div>
      </Link>
      <Link
        href={href as never}
        className="flex min-w-0 items-center gap-1.5"
        style={{ fontSize: 12 }}
      >
        <CountryFlag cc={country} />
        <span className="truncate">{city ?? country ?? '—'}</span>
      </Link>
      <Link
        href={href as never}
        className="mono truncate text-fg-secondary md:block hidden"
        style={{ fontSize: 11 }}
        data-testid="device-block"
      >
        {device ?? 'device unknown'}
      </Link>
      <Link href={href as never} className="flex flex-wrap gap-1">
        {features.map((f) => (
          <ShapFeatureChip key={`${f.feature_name}-${f.shap_value}`} feature={f} />
        ))}
        {features.length === 0 && <span className="text-11 text-fg-quaternary">no shap</span>}
      </Link>
      <Link href={href as never} className="text-right">
        <span
          className="num mono inline-flex min-w-[36px] justify-center rounded-r-sm px-1.5 py-0.5 text-12 font-semibold"
          style={{ background: colour.bg, color: colour.fg }}
          aria-label={`Score ${Math.round(score.normalised_score * 100)}${isAnomalous ? ', flagged' : ''}`}
        >
          {Math.round(score.normalised_score * 100)}
        </span>
      </Link>
    </div>
  );
}
