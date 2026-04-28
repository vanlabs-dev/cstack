import { cn } from '@/lib/cn';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden
      className={cn('animate-pulse rounded-r-sm bg-surface-subtle', className)}
      {...props}
    />
  );
}
