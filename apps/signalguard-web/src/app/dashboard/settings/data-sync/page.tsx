export default function DataSyncPage() {
  return (
    <div className="rounded-r-md border border-border bg-surface p-5">
      <p className="eyebrow mb-2">Data &amp; sync</p>
      <h2 className="text-16 font-semibold">Coming in V2 with API support</h2>
      <p className="mt-2 max-w-[640px] text-13 text-fg-secondary">
        Configure ingestion cadence and historical retention for each tenant. Currently the ingest
        pipeline runs from the CLI and the dashboard reads the latest fixture state.
      </p>
      <ul className="mt-3 max-w-[640px] list-disc space-y-1 pl-5 text-13 text-fg-secondary">
        <li>Per-resource refresh schedule.</li>
        <li>Sign-in retention window.</li>
        <li>Manual full-resync controls.</li>
      </ul>
    </div>
  );
}
