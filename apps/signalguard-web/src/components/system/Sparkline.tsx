'use client';

import { Area, AreaChart, ResponsiveContainer } from 'recharts';

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
      data-testid="sparkline"
    >
      <polyline points={area} fill={color} fillOpacity="0.08" stroke="none" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.25" />
    </svg>
  );
}

interface KpiSparklineProps {
  data: number[];
  color?: string;
  height?: number;
  className?: string;
}

/**
 * recharts-backed sparkline with smooth monotone interpolation, ~32px tall.
 * Use this on KPI cards where you want a real chart with hover affordance.
 */
export function KpiSparkline({
  data,
  color = 'var(--color-brand)',
  height = 32,
  className,
}: KpiSparklineProps) {
  const series = data.map((value, index) => ({ index, value }));
  return (
    <div className={className} data-testid="kpi-sparkline">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={series} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={color}
            fillOpacity={0.12}
            isAnimationActive={false}
            dot={false}
            activeDot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
