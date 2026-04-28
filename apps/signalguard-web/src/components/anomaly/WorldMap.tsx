/**
 * Inline SVG world map for the anomaly drill-down location card. Continents
 * are stylised low-detail blobs so we avoid shipping a heavy GeoJSON or
 * reaching for Leaflet/Mapbox. Country dots are positioned by lat/long via
 * the equirectangular projection helper below.
 */

interface WorldMapProps {
  pin: { country: string | null; lat: number | null; lon: number | null };
  history: Array<{ lat: number | null; lon: number | null }>;
  width?: number | string;
  height?: number;
}

const VIEW_W = 600;
const VIEW_H = 280;

function project(lat: number, lon: number): { x: number; y: number } {
  // Equirectangular projection clipped to a 600x280 viewBox.
  const x = ((lon + 180) / 360) * VIEW_W;
  const y = ((90 - lat) / 180) * VIEW_H;
  return { x, y };
}

export function WorldMap({ pin, history, width = '100%', height = 130 }: WorldMapProps) {
  const pinPoint = pin.lat !== null && pin.lon !== null ? project(pin.lat, pin.lon) : null;
  const historyPoints = history
    .filter((h): h is { lat: number; lon: number } => h.lat !== null && h.lon !== null)
    .map((h) => project(h.lat, h.lon));
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Sign-in location ${pin.country ?? 'unknown'} versus typical pattern`}
      style={{ background: 'var(--color-surface-subtle)', display: 'block' }}
    >
      <defs>
        <pattern id="world-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0H0V20" fill="none" stroke="var(--color-border)" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width={VIEW_W} height={VIEW_H} fill="url(#world-grid)" />
      {/* Stylised continent blobs */}
      <path
        d="M40 80 Q90 55 160 70 T270 80 Q300 95 305 130 L280 155 Q210 165 150 150 T80 130 Q45 115 40 80 Z"
        fill="var(--color-border-subtle)"
        stroke="var(--color-border)"
        strokeWidth="0.6"
      />
      <path
        d="M310 70 Q360 50 430 65 T510 80 Q540 95 550 125 L520 150 Q470 160 410 150 T340 135 Q310 120 310 70 Z"
        fill="var(--color-border-subtle)"
        stroke="var(--color-border)"
        strokeWidth="0.6"
      />
      <path
        d="M100 180 Q160 175 200 200 Q220 230 200 250 Q160 260 130 250 Q100 235 100 180 Z"
        fill="var(--color-border-subtle)"
        stroke="var(--color-border)"
        strokeWidth="0.6"
      />
      <path
        d="M380 200 Q420 195 450 215 Q470 235 460 250 Q430 260 405 250 Q380 235 380 200 Z"
        fill="var(--color-border-subtle)"
        stroke="var(--color-border)"
        strokeWidth="0.6"
      />
      {/* Typical countries as soft green dots */}
      {historyPoints.map((p, i) => (
        <circle key={`hist-${i}`} cx={p.x} cy={p.y} r="3" fill="var(--color-ok)" opacity="0.45" />
      ))}
      {/* Current sign-in highlighted in critical red */}
      {pinPoint && (
        <>
          <circle cx={pinPoint.x} cy={pinPoint.y} r="14" fill="var(--color-crit)" opacity="0.12" />
          <circle cx={pinPoint.x} cy={pinPoint.y} r="7" fill="var(--color-crit)" opacity="0.28" />
          <circle cx={pinPoint.x} cy={pinPoint.y} r="3.5" fill="var(--color-crit)" />
        </>
      )}
    </svg>
  );
}
