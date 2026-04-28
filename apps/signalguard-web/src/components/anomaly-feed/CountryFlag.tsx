interface CountryFlagProps {
  cc: string | null | undefined;
  className?: string;
}

/**
 * Lightweight country code chip. We don't ship real flags to keep the bundle
 * small and avoid licensing churn; a 2-letter mono chip is the convention
 * the design's reference screen uses.
 */
export function CountryFlag({ cc, className }: CountryFlagProps) {
  const display = (cc ?? '??').slice(0, 2).toUpperCase();
  return (
    <span
      className={className}
      role="img"
      aria-label={`Country ${display}`}
      style={{
        width: 22,
        height: 14,
        fontSize: 9,
        fontFamily: 'var(--font-mono)',
        display: 'inline-grid',
        placeItems: 'center',
        background: 'var(--color-surface-subtle)',
        border: '1px solid var(--color-border)',
        borderRadius: 2,
        color: 'var(--color-fg-secondary)',
        fontWeight: 600,
        flex: 'none',
      }}
    >
      {display}
    </span>
  );
}
