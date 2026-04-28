import { Skeleton } from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex h-screen w-full bg-bg">
      <div className="h-full w-[224px] flex-none border-r border-border bg-surface" />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="h-11 flex-none border-b border-border bg-surface" />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-6">
            <div className="mb-4 flex items-center gap-3">
              <Skeleton className="h-9 w-9 rounded-full" />
              <div className="flex-1">
                <Skeleton className="mb-1 h-5 w-72" />
                <Skeleton className="h-3 w-96" />
              </div>
              <Skeleton className="h-6 w-20" />
            </div>
            <div
              className="grid gap-3.5"
              style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.05fr)' }}
            >
              <Skeleton className="h-[640px] w-full" />
              <div className="space-y-3">
                <Skeleton className="h-[160px] w-full" />
                <Skeleton className="h-[260px] w-full" />
                <Skeleton className="h-[120px] w-full" />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
