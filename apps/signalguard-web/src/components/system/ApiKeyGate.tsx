"use client";

import { useEffect, useState } from "react";

import { getApiKey, setApiKey } from "@/lib/api/key-storage";

interface ApiKeyGateProps {
  children: React.ReactNode;
}

export function ApiKeyGate({ children }: ApiKeyGateProps) {
  const [resolved, setResolved] = useState<boolean>(false);
  const [hasKey, setHasKey] = useState<boolean>(false);
  const [draft, setDraft] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);

  useEffect(() => {
    setHasKey(getApiKey() !== null);
    setResolved(true);
  }, []);

  if (!resolved) {
    return null;
  }

  if (hasKey) {
    return <>{children}</>;
  }

  const onSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!draft.trim() || submitting) return;
    setSubmitting(true);
    setApiKey(draft.trim());
    window.location.reload();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg">
      <form
        onSubmit={onSubmit}
        className="w-[360px] rounded-r-md border border-border bg-surface p-6"
        style={{ boxShadow: "var(--shadow-modal)" }}
      >
        <div className="mb-1 flex items-center gap-2">
          <span
            className="grid h-6 w-6 place-items-center rounded-r-md text-white"
            style={{
              background: "linear-gradient(135deg, #1A1A19 0%, #3A3A37 100%)",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            c
          </span>
          <span className="text-14 font-semibold tracking-[-0.012em]">cstack</span>
        </div>
        <h1 className="mb-1 text-16 font-semibold">Enter dev API key</h1>
        <p className="mb-4 text-13 text-fg-tertiary">
          The signalguard-api dev key, configured locally via{" "}
          <code className="mono text-12 text-fg">SIGNALGUARD_API_DEV_API_KEY</code>.
        </p>
        <label
          htmlFor="api-key"
          className="eyebrow mb-1.5 block"
        >
          API key
        </label>
        <input
          id="api-key"
          name="api-key"
          type="password"
          autoComplete="off"
          required
          autoFocus
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="mb-4 h-8 w-full rounded-r border border-border bg-surface-inset px-3 text-13 text-fg outline-none transition-colors focus:border-brand"
          placeholder="dev-secret"
        />
        <button
          type="submit"
          disabled={!draft.trim() || submitting}
          className="inline-flex h-8 w-full items-center justify-center rounded-r border border-brand bg-brand px-3 text-13 font-medium text-white transition-colors hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          Continue
        </button>
      </form>
    </div>
  );
}
