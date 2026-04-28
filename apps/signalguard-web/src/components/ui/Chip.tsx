import { forwardRef } from 'react';

import { cn } from '@/lib/cn';

export interface ChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

export const Chip = forwardRef<HTMLButtonElement, ChipProps>(
  ({ className, active = false, ...props }, ref) => (
    <button
      ref={ref}
      type={props.type ?? 'button'}
      className={cn(
        'inline-flex h-[22px] items-center gap-1.5 rounded-r-sm border px-2 text-12 transition-colors',
        active
          ? 'border-fg bg-fg text-bg hover:border-fg'
          : 'border-border bg-surface text-fg-secondary hover:border-border-strong',
        className,
      )}
      {...props}
    />
  ),
);
Chip.displayName = 'Chip';
