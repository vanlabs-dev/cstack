import { forwardRef } from 'react';

import { cn } from '@/lib/cn';

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = 'text', ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        'h-8 w-full rounded-r border border-border bg-surface-inset px-3 text-13 text-fg outline-none transition-colors placeholder:text-fg-quaternary focus:border-brand',
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = 'Input';
