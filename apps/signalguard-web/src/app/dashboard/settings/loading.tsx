import { Skeleton } from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div>
      <Skeleton className="mb-4 h-9 w-full" />
      <Skeleton className="h-[480px] w-full" />
    </div>
  );
}
