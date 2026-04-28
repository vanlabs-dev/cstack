export default function IntegrationsPage() {
  return (
    <div className="rounded-r-md border border-border bg-surface p-5">
      <p className="eyebrow mb-2">Integrations</p>
      <h2 className="text-16 font-semibold">Coming in V2 with API support</h2>
      <p className="mt-2 max-w-[640px] text-13 text-fg-secondary">
        Outbound integrations live here once the platform exposes hook points: SIEM forwarders, ITSM
        systems, and PSA platforms used by MSPs.
      </p>
      <ul className="mt-3 max-w-[640px] list-disc space-y-1 pl-5 text-13 text-fg-secondary">
        <li>SIEM webhook for new findings.</li>
        <li>ITSM ticket open on critical anomalies.</li>
        <li>ConnectWise / Halo PSA contract sync.</li>
      </ul>
    </div>
  );
}
