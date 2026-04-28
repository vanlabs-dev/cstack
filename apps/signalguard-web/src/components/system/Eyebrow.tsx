import { cn } from '@/lib/cn';

export interface EyebrowProps {
  children: React.ReactNode;
  className?: string;
}

export function Eyebrow({ children, className }: EyebrowProps) {
  return <p className={cn('eyebrow', className)}>{children}</p>;
}
