export default function NotificationsPage() {
  return (
    <div className="rounded-r-md border border-border bg-surface p-5">
      <p className="eyebrow mb-2">Notifications</p>
      <h2 className="text-16 font-semibold">Coming in V2 with API support</h2>
      <p className="mt-2 max-w-[640px] text-13 text-fg-secondary">
        The plan is per-tenant routing of new findings and high-score anomalies into Slack,
        Microsoft Teams, or email. The settings UI will live here once the API exposes notification
        routes and templates.
      </p>
      <ul className="mt-3 max-w-[640px] list-disc space-y-1 pl-5 text-13 text-fg-secondary">
        <li>Per-channel severity floor and quiet hours.</li>
        <li>Per-rule muting and digesting policy.</li>
        <li>Audit log of sent notifications.</li>
      </ul>
    </div>
  );
}
