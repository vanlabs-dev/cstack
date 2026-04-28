interface TenantTileProps {
  name: string;
  size?: number;
  className?: string;
}

const TILE_PALETTE = [
  'linear-gradient(135deg, #1F3F66 0%, #2E5A8C 100%)',
  'linear-gradient(135deg, #4F2E66 0%, #6F4E8B 100%)',
  'linear-gradient(135deg, #1F664F 0%, #2E8B73 100%)',
  'linear-gradient(135deg, #663F1F 0%, #8B5A2E 100%)',
  'linear-gradient(135deg, #66301F 0%, #8B4D2E 100%)',
  'linear-gradient(135deg, #1F4F66 0%, #2E6F8B 100%)',
];

function tileBackground(name: string): string {
  const seed = name.length === 0 ? 0 : name.charCodeAt(0);
  return TILE_PALETTE[seed % TILE_PALETTE.length]!;
}

function letters(name: string): string {
  return name
    .split(/[\s-]+/)
    .map((w) => w[0] ?? '')
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export function TenantTile({ name, size = 18, className }: TenantTileProps) {
  return (
    <span
      className={className}
      style={{
        width: size,
        height: size,
        flex: 'none',
        background: tileBackground(name),
        color: '#fff',
        fontSize: size * 0.5,
        fontWeight: 700,
        borderRadius: 3,
        display: 'grid',
        placeItems: 'center',
        letterSpacing: '0.02em',
      }}
      aria-hidden
    >
      {letters(name)}
    </span>
  );
}
