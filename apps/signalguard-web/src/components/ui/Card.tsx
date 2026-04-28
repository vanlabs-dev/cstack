import { forwardRef } from 'react';

import { cn } from '@/lib/cn';

export const Card = forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }
>(({ className, hover = false, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-r-md border border-border bg-surface',
      hover &&
        'transition-colors duration-[var(--duration-base)] ease-[var(--ease-cs)] hover:border-border-strong',
      className,
    )}
    {...props}
  />
));
Card.displayName = 'Card';

export const CardHeader = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'flex items-center justify-between border-b border-border px-3.5 py-3',
        className,
      )}
      {...props}
    />
  ),
);
CardHeader.displayName = 'CardHeader';

export const CardTitle = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('text-13 font-semibold', className)} {...props} />
  ),
);
CardTitle.displayName = 'CardTitle';

export const CardSub = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('mt-0.5 text-[11.5px] text-fg-tertiary', className)} {...props} />
  ),
);
CardSub.displayName = 'CardSub';

export const CardBody = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn('p-3.5', className)} {...props} />,
);
CardBody.displayName = 'CardBody';
