import Link from 'next/link';

import { Avatar } from '@/components/system/Avatar';
import { formatRelativeTime } from '@/lib/format';

import type { AnomalyScore } from '@/lib/api/generated/types.gen';

interface AnomalySummaryRowProps {
  score: AnomalyScore;
  tenantId: string;
  isLast: boolean;
}

function scoreColor(score: number): { fg: string; bg: string } {
  if (score >= 0.95) return { fg: 'var(--color-crit)', bg: 'var(--color-crit-bg)' };
  if (score >= 0.85) return { fg: 'var(--color-high)', bg: 'var(--color-high-bg)' };
  if (score >= 0.7) return { fg: 'var(--color-med)', bg: 'var(--color-med-bg)' };
  return { fg: 'var(--color-low)', bg: 'var(--color-low-bg)' };
}

function topReason(score: AnomalyScore): string {
  const top = (score.shap_top_features ?? [])
    .filter((f) => f.direction === 'pushes_anomalous')
    .slice(0, 2)
    .map((f) => f.feature_name);
  return top.length > 0 ? top.join(' · ') : 'no shap attribution';
}

export function AnomalySummaryRow({ score, tenantId, isLast }: AnomalySummaryRowProps) {
  const colour = scoreColor(score.normalised_score);
  return (
    <Link
      href={
        `/dashboard/anomalies/${encodeURIComponent(score.signin_id)}?tenant=${tenantId}` as never
      }
      className="grid items-center gap-2.5 px-3.5 py-2.5 transition-colors hover:bg-surface-hover"
      style={{
        gridTemplateColumns: 'auto 1fr auto',
        borderBottom: isLast ? 'none' : '1px solid var(--color-border-subtle)',
      }}
    >
      <Avatar name={score.user_id} size={24} />
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate text-13 font-medium">{score.user_id}</span>
          <span className="mono whitespace-nowrap text-fg-quaternary" style={{ fontSize: 10.5 }}>
            {formatRelativeTime(score.scored_at)}
          </span>
        </div>
        <div className="mono mt-0.5 truncate text-fg-tertiary" style={{ fontSize: 11 }}>
          {topReason(score)}
        </div>
      </div>
      <span
        className="num mono inline-flex min-w-[32px] justify-center rounded-r-sm px-1.5 py-0.5 text-12 font-semibold"
        style={{ background: colour.bg, color: colour.fg }}
      >
        {Math.round(score.normalised_score * 100)}
      </span>
    </Link>
  );
}
