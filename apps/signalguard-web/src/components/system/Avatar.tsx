interface AvatarProps {
  name: string;
  size?: number;
  className?: string;
}

const PALETTE = [
  '#6B5B95',
  '#88A04F',
  '#955251',
  '#5B7B95',
  '#7E6B8F',
  '#C2880C',
  '#0F766E',
  '#925E7B',
];

function deterministicColor(name: string): string {
  if (name.length === 0) return PALETTE[0]!;
  return PALETTE[name.charCodeAt(0) % PALETTE.length]!;
}

function initials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0] ?? '')
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

export function Avatar({ name, size = 22, className }: AvatarProps) {
  const color = deterministicColor(name);
  return (
    <span
      className={className}
      style={{
        width: size,
        height: size,
        flex: 'none',
        borderRadius: '50%',
        background: color,
        color: '#fff',
        fontSize: size * 0.42,
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        letterSpacing: 0,
      }}
      aria-label={`Avatar for ${name}`}
    >
      {initials(name)}
    </span>
  );
}
