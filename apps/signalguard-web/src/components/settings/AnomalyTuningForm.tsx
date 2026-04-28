'use client';

import { useEffect, useState } from 'react';

import { FormRow } from '@/components/settings/FormRow';
import { Button } from '@/components/ui/Button';

import type { ModelSummary } from '@/lib/api/generated/types.gen';

const THRESHOLD_KEY = 'cstack-anomaly-threshold';

interface AnomalyTuningFormProps {
  models: ModelSummary[];
}

export function AnomalyTuningForm({ models }: AnomalyTuningFormProps) {
  const [threshold, setThreshold] = useState<number>(0.7);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const persisted = window.localStorage.getItem(THRESHOLD_KEY);
    if (persisted) setThreshold(Number(persisted));
  }, []);

  const onSave = (): void => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(THRESHOLD_KEY, String(threshold));
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1500);
  };

  const champion = models.find((m) => m.current_champion_version !== null);
  const metrics = champion?.training_metrics ?? {};

  return (
    <div className="space-y-4">
      <div className="rounded-r-md border border-border bg-surface px-4 py-1">
        <FormRow
          label="Current model"
          description="The pooled per-tenant Isolation Forest in MLflow."
        >
          {champion ? (
            <div className="space-y-1 text-13">
              <div>
                <span className="mono text-fg">{champion.name}</span>
                <span className="ml-2 mono text-fg-tertiary">
                  v{champion.current_champion_version}
                </span>
              </div>
              <div className="mono text-12 text-fg-tertiary">
                Last trained{' '}
                {champion.last_trained_at
                  ? new Date(champion.last_trained_at).toISOString().slice(0, 10)
                  : 'unknown'}
              </div>
            </div>
          ) : (
            <p className="text-13 text-fg-tertiary">
              No champion model registered. Run{' '}
              <code className="mono text-fg">cstack anomaly train --tenant &lt;id&gt;</code>.
            </p>
          )}
        </FormRow>

        <FormRow
          label="Detection threshold"
          description="Score above which findings are emitted. Currently a global preference; per-tenant tuning lands once the API exposes a setter."
        >
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0.5}
              max={0.99}
              step={0.01}
              value={threshold}
              onChange={(event) => setThreshold(Number(event.target.value))}
              aria-label="Detection threshold"
              className="flex-1 accent-brand"
            />
            <span className="mono w-14 text-right text-13 font-medium">{threshold.toFixed(2)}</span>
          </div>
        </FormRow>

        <FormRow
          label="Recent calibration"
          description="Metrics captured at the last training run."
        >
          {Object.keys(metrics).length === 0 ? (
            <p className="text-12 text-fg-tertiary">No metrics recorded yet.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 text-13 md:grid-cols-3">
              {Object.entries(metrics).map(([k, v]) => (
                <div key={k} className="rounded-r-sm bg-surface-inset px-2.5 py-1.5">
                  <div className="mono text-11 text-fg-tertiary">{k}</div>
                  <div className="num font-medium">{Number(v).toFixed(2)}</div>
                </div>
              ))}
            </div>
          )}
        </FormRow>

        <div className="flex flex-wrap items-center gap-3 py-4">
          <Button variant="primary" onClick={onSave}>
            Save preferences
          </Button>
          {saved && <span className="text-12 text-ok">Saved.</span>}
        </div>
      </div>

      <div className="rounded-r-md border border-border bg-surface px-4 py-1">
        <FormRow
          label="Retrain model"
          description="MLflow lifecycle is driven from the CLI in this sprint. Web-trigger lands once the API exposes the runner."
        >
          <Button variant="default" disabled aria-label="Retrain model">
            Retrain (CLI only)
          </Button>
        </FormRow>
        <FormRow
          label="Promote challenger"
          description="Move the @champion alias to the current @challenger version. CLI-only for now."
        >
          <Button variant="default" disabled aria-label="Force promote challenger">
            Force promote (CLI only)
          </Button>
        </FormRow>
        <FormRow label="View training runs" description="Launch the local MLflow UI.">
          <code className="mono inline-block rounded-r-sm bg-surface-inset px-2 py-1 text-12">
            mlflow ui --backend-store-uri file://./mlruns
          </code>
        </FormRow>
      </div>
    </div>
  );
}
