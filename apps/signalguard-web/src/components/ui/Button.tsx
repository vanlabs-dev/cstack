import { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/cn';

const buttonVariants = cva(
  'inline-flex items-center gap-1.5 whitespace-nowrap rounded-r font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-60',
  {
    variants: {
      variant: {
        default:
          'border border-border bg-surface text-fg hover:bg-surface-hover hover:border-border-strong shadow-[0_1px_0_rgba(15,15,20,0.02)]',
        primary:
          'border border-brand bg-brand text-white hover:bg-brand-hover hover:border-brand-hover shadow-[0_1px_0_rgba(15,15,20,0.08),inset_0_1px_0_rgba(255,255,255,0.12)]',
        ghost:
          'border border-transparent bg-transparent text-fg-secondary hover:bg-surface-hover hover:text-fg',
        success: 'border border-transparent bg-ok-bg text-ok hover:brightness-95',
      },
      size: {
        sm: 'h-6 px-2 text-12',
        default: 'h-7 px-2.5 text-13',
        lg: 'h-8 px-3 text-13',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      type={props.type ?? 'button'}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = 'Button';

export { buttonVariants };
