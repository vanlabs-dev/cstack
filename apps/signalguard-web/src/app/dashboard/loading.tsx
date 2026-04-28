import { Skeleton } from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex h-screen w-full bg-bg">
      <div className="h-full w-[224px] flex-none border-r border-border bg-surface" />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="h-11 flex-none border-b border-border bg-surface" />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-6">
            <Skeleton className="mb-2 h-3 w-32" />
            <Skeleton className="mb-6 h-7 w-72" />
            <div className="mb-6 grid gap-2.5" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-[148px] w-full" />
              ))}
            </div>
            <div
              className="grid gap-4"
              style={{ gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)' }}
            >
              <Skeleton className="h-[400px] w-full" />
              <Skeleton className="h-[400px] w-full" />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
