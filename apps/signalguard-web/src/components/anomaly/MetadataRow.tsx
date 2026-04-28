import { CopyButton } from '@/components/findings/CopyButton';
import { cn } from '@/lib/cn';

interface MetadataRowProps {
  label: string;
  value: string | number | boolean | null | undefined;
  mono?: boolean;
  copy?: boolean;
  flag?: boolean;
  isLast?: boolean;
}

export function MetadataRow({
  label,
  value,
  mono = false,
  copy = false,
  flag = false,
  isLast = false,
}: MetadataRowProps) {
  const display =
    value === null || value === undefined || value === ''
      ? '—'
      : typeof value === 'boolean'
        ? String(value)
        : String(value);
  return (
    <div
      className="grid items-center gap-3 px-3.5 py-1.5"
      style={{
        gridTemplateColumns: '200px 1fr auto',
        borderBottom: isLast ? 'none' : '1px dashed var(--color-border-subtle)',
      }}
    >
      <span className="text-12 text-fg-tertiary">{label}</span>
      <span className={cn('text-13 break-words', mono && 'mono', flag && 'text-crit')}>
        {display}
      </span>
      {copy && display !== '—' ? <CopyButton text={display} label="Copy" /> : <span aria-hidden />}
    </div>
  );
}
