import { Skeleton } from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex h-screen w-full bg-bg">
      <div className="h-full w-[224px] flex-none border-r border-border bg-surface" />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="h-11 flex-none border-b border-border bg-surface" />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-6">
            <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(0, 1fr) 240px' }}>
              <div>
                <Skeleton className="mb-2 h-3 w-48" />
                <Skeleton className="mb-1 h-7 w-32" />
                <Skeleton className="mb-4 h-3 w-72" />
                <Skeleton className="mb-3 h-9 w-full" />
                <Skeleton className="h-[480px] w-full" />
              </div>
              <div className="space-y-2.5">
                <Skeleton className="h-[120px] w-full" />
                <Skeleton className="h-[160px] w-full" />
                <Skeleton className="h-[140px] w-full" />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
