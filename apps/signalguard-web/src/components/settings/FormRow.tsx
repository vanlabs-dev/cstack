interface FormRowProps {
  label: string;
  description?: string;
  children: React.ReactNode;
}

export function FormRow({ label, description, children }: FormRowProps) {
  return (
    <div className="grid gap-3 border-b border-border-subtle py-4 last:border-b-0 md:grid-cols-[260px_1fr] md:items-start md:gap-6">
      <div>
        <div className="text-13 font-medium">{label}</div>
        {description && (
          <p className="mt-0.5 text-12 leading-[1.5] text-fg-tertiary">{description}</p>
        )}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
