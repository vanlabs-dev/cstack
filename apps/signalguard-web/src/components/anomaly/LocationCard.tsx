import type { AnomalyScoreDetail } from '@/lib/api/generated/types.gen';

interface LocationCardProps {
  detail: AnomalyScoreDetail;
  typicalCountries: string[];
  distanceFromLastKm: number | null;
}

export function LocationCard({ detail, typicalCountries, distanceFromLastKm }: LocationCardProps) {
  const loc = detail.signin.location ?? null;
  const country = loc?.countryOrRegion ?? '—';
  const city = loc?.city ?? '—';
  return (
    <div className="overflow-hidden rounded-r-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-3">
        <div>
          <div className="text-13 font-semibold">Location</div>
          <div className="mt-0.5 text-11 text-fg-tertiary">This sign-in vs typical pattern</div>
        </div>
        <span className="mono text-11 text-fg-tertiary">{detail.signin.ipAddress ?? '—'}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 p-3.5 text-13">
        <div>
          <p className="eyebrow mb-1">This sign-in</p>
          <div className="font-medium">{city}</div>
          <div className="text-fg-tertiary">{country}</div>
        </div>
        <div>
          <p className="eyebrow mb-1">Typical countries</p>
          <div className="flex flex-wrap gap-1">
            {typicalCountries.length === 0 ? (
              <span className="text-fg-tertiary">No history yet</span>
            ) : (
              typicalCountries.slice(0, 6).map((c) => (
                <span
                  key={c}
                  className="rounded-r-sm border border-border-subtle bg-surface-subtle px-1.5 py-0.5 text-11 text-fg-secondary"
                >
                  {c}
                </span>
              ))
            )}
          </div>
        </div>
      </div>
      <div className="border-t border-border-subtle px-3.5 py-2 text-11 text-fg-tertiary">
        {distanceFromLastKm === null
          ? 'Map view in 5b'
          : `~${Math.round(distanceFromLastKm).toLocaleString()} km from previous sign-in`}
      </div>
    </div>
  );
}
