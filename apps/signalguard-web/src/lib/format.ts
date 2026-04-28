/**
 * Tone-of-UI formatters. Sentence case, no marketing language, no emoji.
 *
 * `formatRelativeTime` returns the same shape the design uses: "2m ago",
 * "5h ago", "3d ago". The helper avoids date-fns' verbose phrasing
 * (`about 2 hours ago`) which clashes with the design system's tone.
 */

export function formatRelativeTime(input: string | Date | null | undefined): string {
  if (!input) return '—';
  const d = typeof input === 'string' ? new Date(input) : input;
  if (Number.isNaN(d.getTime())) return '—';
  const diffMs = Date.now() - d.getTime();
  if (diffMs < 0) return 'now';
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 45) return 'now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  const years = Math.floor(days / 365);
  return `${years}y ago`;
}

export function timeOfDay(now: Date = new Date()): 'morning' | 'afternoon' | 'evening' {
  const h = now.getHours();
  if (h < 12) return 'morning';
  if (h < 18) return 'afternoon';
  return 'evening';
}

export function shortTenantId(id: string): string {
  if (id.length <= 12) return id;
  return id.slice(0, 8);
}
