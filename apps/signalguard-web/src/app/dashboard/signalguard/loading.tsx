import { Skeleton } from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex h-screen w-full bg-bg">
      <div className="h-full w-[224px] flex-none border-r border-border bg-surface" />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="h-11 flex-none border-b border-border bg-surface" />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-6">
            <Skeleton className="mb-2 h-3 w-44" />
            <Skeleton className="mb-1 h-7 w-32" />
            <Skeleton className="mb-5 h-3 w-72" />
            <div className="mb-4 grid gap-2.5 md:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[120px] w-full" />
              ))}
            </div>
            <div className="mb-4 grid gap-3 md:grid-cols-2">
              <Skeleton className="h-[320px] w-full" />
              <Skeleton className="h-[320px] w-full" />
            </div>
            <Skeleton className="mb-4 h-[260px] w-full" />
            <Skeleton className="h-[80px] w-full" />
          </div>
        </main>
      </div>
    </div>
  );
}
