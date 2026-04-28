interface SparklineProps {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
  className?: string;
}

export function Sparkline({
  data,
  color = 'var(--color-brand)',
  width = 88,
  height = 26,
  className,
}: SparklineProps) {
  if (data.length < 2) {
    return <svg width={width} height={height} className={className} aria-hidden />;
  }
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const area = `0,${height} ${pts} ${width},${height}`;
  return (
    <svg
      width={width}
      height={height}
      className={className}
      role="img"
      aria-label="trend sparkline"
    >
      <polyline points={area} fill={color} fillOpacity="0.08" stroke="none" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.25" />
    </svg>
  );
}
